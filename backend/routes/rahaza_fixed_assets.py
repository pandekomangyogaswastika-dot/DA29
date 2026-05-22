"""
CV. Dewi Aditya ERP — Fixed Asset & Depreciation (Session 11)

Endpoints (prefix /api/rahaza/finance):
  GET    /fixed-assets                   — list aset tetap
  POST   /fixed-assets                   — daftarkan aset baru
  GET    /fixed-assets/{id}              — detail + jadwal depresiasi
  PUT    /fixed-assets/{id}              — update
  POST   /fixed-assets/{id}/dispose      — disposal aset
  GET    /fixed-assets/{id}/schedule     — jadwal depresiasi lengkap
  POST   /fixed-assets/{id}/post-depr/{period} — posting depresiasi periode YYYY-MM
  GET    /fixed-assets/depreciation-due  — daftar aset perlu posting depresiasi
  GET    /fixed-assets-summary           — ringkasan portfolio (total cost, NBV, akumulasi)

Koleksi: rahaza_fixed_assets, rahaza_depr_schedules
"""
from fastapi import APIRouter, Request, HTTPException
from database import get_db
from auth import require_auth, serialize_doc
from routes.shared import get_pagination_params, paginated_response
from datetime import datetime, timezone, date
from dateutil.relativedelta import relativedelta
from typing import Optional
import uuid
import math
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rahaza/finance", tags=["rahaza-fixed-assets"])

def _uid(): return str(uuid.uuid4())
def _now(): return datetime.now(timezone.utc)

ASSET_CATEGORIES = ["tanah", "bangunan", "mesin", "kendaraan", "peralatan", "it", "furnitur", "lain-lain"]
DEPR_METHODS    = ["straight_line", "double_declining"]


# ─── HELPER: generate depreciation schedule ────────────────────────────────

def _generate_schedule(asset: dict) -> list:
    """
    Generate monthly depreciation schedule for the asset.
    Returns list of {period, depr_amount, accumulated_depr, book_value_start, book_value_end}
    """
    cost       = float(asset.get("purchase_cost") or 0)
    residual   = float(asset.get("residual_value") or 0)
    useful_life = int(asset.get("useful_life_months") or 12)
    method      = asset.get("depreciation_method", "straight_line")
    start_date_str = asset.get("purchase_date") or date.today().isoformat()
    try:
        start_date = date.fromisoformat(start_date_str[:10])
    except ValueError:
        start_date = date.today()
    # Start depreciation from the month AFTER purchase (or first day of purchase month)
    depr_start = date(start_date.year, start_date.month, 1)
    depr_end   = depr_start + relativedelta(months=useful_life)

    schedule = []
    book_value = cost
    accumulated = 0.0
    if method == "straight_line":
        monthly_depr = round((cost - residual) / useful_life, 2) if useful_life > 0 else 0
        for i in range(useful_life):
            period_date = depr_start + relativedelta(months=i)
            period_str  = period_date.strftime("%Y-%m")
            bv_start    = round(book_value, 2)
            depr_amt    = min(monthly_depr, max(0, book_value - residual))
            depr_amt    = round(depr_amt, 2)
            accumulated = round(accumulated + depr_amt, 2)
            book_value  = round(book_value - depr_amt, 2)
            schedule.append({
                "period":          period_str,
                "book_value_start": bv_start,
                "depr_amount":     depr_amt,
                "accumulated_depr": accumulated,
                "book_value_end":  book_value,
            })
    elif method == "double_declining":
        rate = 2 / useful_life if useful_life > 0 else 0
        for i in range(useful_life):
            period_date = depr_start + relativedelta(months=i)
            period_str  = period_date.strftime("%Y-%m")
            bv_start    = round(book_value, 2)
            depr_amt    = round(book_value * rate / 12, 2)  # monthly rate
            if book_value - depr_amt < residual:
                depr_amt = max(0, round(book_value - residual, 2))
            accumulated = round(accumulated + depr_amt, 2)
            book_value  = round(book_value - depr_amt, 2)
            schedule.append({
                "period":          period_str,
                "book_value_start": bv_start,
                "depr_amount":     depr_amt,
                "accumulated_depr": accumulated,
                "book_value_end":  book_value,
            })
    return schedule


# ─── CRUD ENDPOINTS ──────────────────────────────────────────────────────────

@router.get("/fixed-assets")
async def list_fixed_assets(request: Request, category: Optional[str] = None,
                             status: Optional[str] = None, search: Optional[str] = None):
    await require_auth(request)
    db = get_db()
    q = {}
    if category: q["category"] = category
    if status:   q["status"]   = status
    else:        q["status"]   = {"$ne": "disposed"}  # default: exclude disposed
    if search:
        import re
        p = re.compile(re.escape(search), re.IGNORECASE)
        q["$or"] = [{"code": p}, {"name": p}, {"serial_number": p}]
    use_pagination = "page" in request.query_params
    if use_pagination:
        page, limit, skip = get_pagination_params(request, default_limit=50)
        total = await db.rahaza_fixed_assets.count_documents(q)
        rows = await db.rahaza_fixed_assets.find(q, {"_id": 0}).sort("purchase_date", -1).skip(skip).limit(limit).to_list(length=10000)
        # Compute current NBV for each
        for r in rows:
            await _enrich_nbv(db, r)
        return paginated_response(serialize_doc(rows), total, page, limit)
    rows = await db.rahaza_fixed_assets.find(q, {"_id": 0}).sort("purchase_date", -1).to_list(500)
    for r in rows:
        await _enrich_nbv(db, r)
    return serialize_doc(rows)


async def _enrich_nbv(db, asset: dict):
    """Add current NBV and accumulated depreciation to asset dict."""
    aid = asset.get("id", "")
    today = date.today().strftime("%Y-%m")
    # Sum all posted depreciation up to today
    pipe = [{"$match": {"asset_id": aid, "period": {"$lte": today}, "posted": True}},
            {"$group": {"_id": None, "total_depr": {"$sum": "$depr_amount"}}}]
    agg = await db.rahaza_depr_schedules.aggregate(pipe).to_list(1)
    accum_depr = round((agg[0]["total_depr"] if agg else 0), 2)
    cost = float(asset.get("purchase_cost") or 0)
    asset["accumulated_depreciation"] = accum_depr
    asset["book_value_current"]       = round(cost - accum_depr, 2)


@router.post("/fixed-assets")
async def create_fixed_asset(request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name: raise HTTPException(400, "Nama aset wajib diisi")
    code = (body.get("code") or "").strip()
    if not code: raise HTTPException(400, "Kode aset wajib diisi")
    if await db.rahaza_fixed_assets.find_one({"code": code}):
        raise HTTPException(409, f"Kode aset '{code}' sudah digunakan")
    cat = body.get("category", "peralatan")
    if cat not in ASSET_CATEGORIES:
        raise HTTPException(400, f"Kategori harus salah satu dari: {ASSET_CATEGORIES}")
    method = body.get("depreciation_method", "straight_line")
    if method not in DEPR_METHODS:
        raise HTTPException(400, f"Metode depresiasi: {DEPR_METHODS}")
    doc = {
        "id":                     _uid(),
        "code":                   code,
        "name":                   name,
        "category":               cat,
        "purchase_date":          body.get("purchase_date") or date.today().isoformat(),
        "purchase_cost":          float(body.get("purchase_cost") or 0),
        "residual_value":         float(body.get("residual_value") or 0),
        "useful_life_months":     int(body.get("useful_life_months") or 60),
        "depreciation_method":    method,
        "account_id_asset":       body.get("account_id_asset"),
        "account_id_accum_depr": body.get("account_id_accum_depr"),
        "account_id_depr_expense": body.get("account_id_depr_expense"),
        "location":               (body.get("location") or "").strip(),
        "supplier":               (body.get("supplier") or "").strip(),
        "serial_number":          (body.get("serial_number") or "").strip(),
        "notes":                  (body.get("notes") or "").strip(),
        "status":                 "active",
        "created_at":             _now(),
        "created_by":             user.get("email"),
        "disposed_at":            None,
        "disposal_notes":         None,
    }
    await db.rahaza_fixed_assets.insert_one(doc)
    # Auto-generate depreciation schedule
    schedule = _generate_schedule(doc)
    if schedule:
        depr_docs = []
        for s in schedule:
            depr_docs.append({
                "id":              _uid(),
                "asset_id":        doc["id"],
                "asset_code":      doc["code"],
                "period":          s["period"],
                "book_value_start":s["book_value_start"],
                "depr_amount":     s["depr_amount"],
                "accumulated_depr":s["accumulated_depr"],
                "book_value_end":  s["book_value_end"],
                "posted":          False,
                "journal_entry_id":None,
                "posted_at":       None,
            })
        if depr_docs:
            await db.rahaza_depr_schedules.insert_many(depr_docs)
    return serialize_doc(doc)


@router.get("/fixed-assets/depreciation-due")
async def depreciation_due(request: Request):
    """Aset yang jadwal depresiasinya belum diposting untuk periode ini."""
    await require_auth(request)
    db = get_db()
    cur_period = date.today().strftime("%Y-%m")
    due = await db.rahaza_depr_schedules.find(
        {"period": cur_period, "posted": False, "depr_amount": {"$gt": 0}},
        {"_id": 0}
    ).to_list(500)
    # Enrich with asset name
    asset_ids = list({d["asset_id"] for d in due})
    assets = {a["id"]: a for a in await db.rahaza_fixed_assets.find({"id": {"$in": asset_ids}}, {"_id": 0}).to_list(500)} if asset_ids else {}
    for d in due:
        a = assets.get(d["asset_id"]) or {}
        d["asset_name"]     = a.get("name", "")
        d["asset_category"] = a.get("category", "")
    return serialize_doc(due)


@router.get("/fixed-assets-summary")
async def fixed_assets_summary(request: Request):
    await require_auth(request)
    db = get_db()
    assets = await db.rahaza_fixed_assets.find({"status": {"$ne": "disposed"}}, {"_id": 0}).to_list(500)
    total_cost = round(sum(float(a.get("purchase_cost") or 0) for a in assets), 2)
    # Accumulated depreciation from all posted schedule entries
    pipe = [{"$match": {"posted": True}},
            {"$group": {"_id": None, "total": {"$sum": "$depr_amount"}}}]
    agg = await db.rahaza_depr_schedules.aggregate(pipe).to_list(1)
    total_accum = round((agg[0]["total"] if agg else 0), 2)
    nbv = round(total_cost - total_accum, 2)
    # Count due this month
    cur_period = date.today().strftime("%Y-%m")
    due_count = await db.rahaza_depr_schedules.count_documents({"period": cur_period, "posted": False, "depr_amount": {"$gt": 0}})
    by_category = {}
    for a in assets:
        cat = a.get("category", "lain-lain")
        if cat not in by_category: by_category[cat] = {"count": 0, "cost": 0}
        by_category[cat]["count"] += 1
        by_category[cat]["cost"]  += float(a.get("purchase_cost") or 0)
    return {
        "total_assets":           len(assets),
        "total_cost":             total_cost,
        "total_accumulated_depr": total_accum,
        "total_nbv":              nbv,
        "depr_due_this_month":    due_count,
        "by_category":            by_category,
    }


@router.get("/fixed-assets/{aid}")
async def get_fixed_asset(aid: str, request: Request):
    await require_auth(request)
    db = get_db()
    asset = await db.rahaza_fixed_assets.find_one({"id": aid}, {"_id": 0})
    if not asset: raise HTTPException(404, "Aset tidak ditemukan")
    await _enrich_nbv(db, asset)
    return serialize_doc(asset)


@router.put("/fixed-assets/{aid}")
async def update_fixed_asset(aid: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    asset = await db.rahaza_fixed_assets.find_one({"id": aid}, {"_id": 0})
    if not asset: raise HTTPException(404, "Aset tidak ditemukan")
    if asset.get("status") == "disposed": raise HTTPException(409, "Aset sudah di-dispose")
    body = await request.json()
    allowed = ["name", "location", "supplier", "serial_number", "notes",
               "account_id_asset", "account_id_accum_depr", "account_id_depr_expense"]
    update = {k: body[k] for k in allowed if k in body}
    if update:
        update["updated_at"] = _now()
        await db.rahaza_fixed_assets.update_one({"id": aid}, {"$set": update})
    out = await db.rahaza_fixed_assets.find_one({"id": aid}, {"_id": 0})
    await _enrich_nbv(db, out)
    return serialize_doc(out)


@router.get("/fixed-assets/{aid}/schedule")
async def get_depr_schedule(aid: str, request: Request):
    await require_auth(request)
    db = get_db()
    rows = await db.rahaza_depr_schedules.find({"asset_id": aid}, {"_id": 0}).sort("period", 1).to_list(length=10000)
    return serialize_doc(rows)


@router.post("/fixed-assets/{aid}/post-depr/{period}")
async def post_depreciation(aid: str, period: str, request: Request):
    """
    Posting depresiasi untuk aset pada periode YYYY-MM.
    Membuat jurnal: Dr Depreciation Expense / Cr Accumulated Depreciation.
    """
    user = await require_auth(request)
    db = get_db()
    asset = await db.rahaza_fixed_assets.find_one({"id": aid}, {"_id": 0})
    if not asset: raise HTTPException(404, "Aset tidak ditemukan")
    if asset.get("status") == "disposed": raise HTTPException(409, "Aset sudah di-dispose")
    sched = await db.rahaza_depr_schedules.find_one({"asset_id": aid, "period": period}, {"_id": 0})
    if not sched: raise HTTPException(404, f"Jadwal depresiasi untuk periode {period} tidak ditemukan")
    if sched.get("posted"): raise HTTPException(409, f"Depresiasi periode {period} sudah diposting")
    depr_amt = float(sched.get("depr_amount") or 0)
    if depr_amt <= 0:
        await db.rahaza_depr_schedules.update_one({"asset_id": aid, "period": period},
            {"$set": {"posted": True, "posted_at": _now()}})
        return {"ok": True, "message": "Jumlah depresiasi 0, posting tanpa jurnal"}
    # Create journal entry if account IDs are configured
    je_id = None
    acc_exp   = asset.get("account_id_depr_expense")
    acc_accum = asset.get("account_id_accum_depr")
    if acc_exp and acc_accum:
        try:
            from routes.rahaza_posting import post_journal
            je_body = {
                "date": f"{period}-01",
                "description": f"Depresiasi {asset['name']} ({asset['code']}) - {period}",
                "reference": f"DEPR/{asset['code']}/{period}",
                "lines": [
                    {"account_id": acc_exp,   "debit": depr_amt, "credit": 0,        "description": f"Depreciation Expense — {asset['name']}"},
                    {"account_id": acc_accum, "debit": 0,        "credit": depr_amt, "description": f"Accumulated Depreciation — {asset['name']}"},
                ],
                "auto_post": True,
            }
            je_id_resp = await post_journal(db, je_body, user)
            je_id = je_id_resp.get("journal_id")
        except Exception as e:
            logger.warning(f"[fixed_assets] Gagal buat jurnal depresiasi: {e}")
    await db.rahaza_depr_schedules.update_one({"asset_id": aid, "period": period}, {"$set": {
        "posted": True,
        "posted_at": _now(),
        "journal_entry_id": je_id,
    }})
    return {"ok": True, "depr_amount": depr_amt, "period": period, "journal_entry_id": je_id}


@router.post("/fixed-assets/{aid}/dispose")
async def dispose_asset(aid: str, request: Request):
    """Disposal aset — tandai sebagai disposed."""
    user = await require_auth(request)
    db = get_db()
    asset = await db.rahaza_fixed_assets.find_one({"id": aid}, {"_id": 0})
    if not asset: raise HTTPException(404, "Aset tidak ditemukan")
    if asset.get("status") == "disposed": raise HTTPException(409, "Aset sudah di-dispose sebelumnya")
    body = await request.json()
    disposal_date  = body.get("disposal_date") or date.today().isoformat()
    disposal_value = float(body.get("disposal_value") or 0)
    disposal_notes = (body.get("notes") or "").strip()
    # Calculate NBV at disposal date
    await _enrich_nbv(db, asset)
    nbv = float(asset.get("book_value_current") or 0)
    gain_loss = round(disposal_value - nbv, 2)
    await db.rahaza_fixed_assets.update_one({"id": aid}, {"$set": {
        "status":        "disposed",
        "disposed_at":   _now(),
        "disposal_date": disposal_date,
        "disposal_value": disposal_value,
        "disposal_notes": disposal_notes,
        "disposal_gain_loss": gain_loss,
        "nbv_at_disposal":    nbv,
    }})
    # Cancel future schedule entries
    await db.rahaza_depr_schedules.update_many(
        {"asset_id": aid, "period": {"$gt": disposal_date[:7]}, "posted": False},
        {"$set": {"cancelled": True}}
    )
    return {"ok": True, "gain_loss": gain_loss, "nbv_at_disposal": nbv}
