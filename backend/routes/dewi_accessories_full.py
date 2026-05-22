"""
Aksesoris Management — Full Implementation (Blueprint §3.3)

Collections:
  acc_items               — Master aksesoris
  acc_stock_movements     — Pergerakan stok (IN/OUT/ADJUST)
  acc_internal_requests   — Request dari divisi internal
  acc_loans               — Peminjaman aksesoris
  acc_opname_sessions     — Sesi stok opname
  acc_opname_lines        — Detail baris opname
  acc_purchase_requests   — Purchase Request ke Finance

Endpoints:
  GET/POST       /api/acc/items
  PUT/DELETE     /api/acc/items/{id}
  GET            /api/acc/stock
  POST           /api/acc/stock/receive   (terima stok masuk)
  POST           /api/acc/stock/issue     (keluarkan stok)
  GET            /api/acc/internal-requests
  POST           /api/acc/internal-requests
  PUT            /api/acc/internal-requests/{id}
  GET/POST       /api/acc/loans
  PUT            /api/acc/loans/{id}/return
  GET/POST       /api/acc/opname
  PUT            /api/acc/opname/{id}
  POST           /api/acc/opname/{id}/complete
  POST           /api/acc/opname/{id}/cancel
  GET/POST       /api/acc/purchase-requests
  PUT            /api/acc/purchase-requests/{id}
  GET            /api/acc/dashboard        (summary)
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import uuid
from datetime import datetime, timezone

from database import get_db
from auth import require_auth, serialize_doc

router = APIRouter(prefix="/api/acc", tags=["accessories-full"])

# ── helpers ──────────────────────────────────────────────────────────────────
def _id():    return str(uuid.uuid4())
def _now():   return datetime.now(timezone.utc).isoformat()
def _uid():   return str(uuid.uuid4())[:8].upper()


async def _stock_qty(db, acc_id: str) -> float:
    """Hitung saldo stok saat ini untuk satu item dari movements."""
    pipeline = [
        {"$match": {"acc_id": acc_id}},
        {"$group": {"_id": None, "total": {"$sum": "$qty_signed"}}}
    ]
    res = await db.acc_stock_movements.aggregate(pipeline).to_list(1)
    return res[0]["total"] if res else 0.0


async def _all_stock(db) -> dict:
    """Return {acc_id: qty} untuk semua item."""
    pipeline = [
        {"$group": {"_id": "$acc_id", "total": {"$sum": "$qty_signed"}}}
    ]
    res = await db.acc_stock_movements.aggregate(pipeline).to_list(500)
    return {r["_id"]: r["total"] for r in res}


# ═══════════════════════════════════════════════════════════════
# MASTER AKSESORIS
# ═══════════════════════════════════════════════════════════════

@router.get("/items")
async def list_items(request: Request):
    user = await require_auth(request)
    db = get_db()
    sp = request.query_params
    query = {"deleted": {"$ne": True}}
    if sp.get("search"):
        import re
        rx = re.compile(sp["search"], re.IGNORECASE)
        query["$or"] = [{"name": rx}, {"code": rx}, {"category": rx}]
    if sp.get("category"):
        query["category"] = sp["category"]

    items = await db.acc_items.find(query, {"_id": 0}).sort("name", 1).to_list(500)
    stock_map = await _all_stock(db)
    for it in items:
        it["stock_qty"] = stock_map.get(it["id"], 0)
        it["stock_status"] = (
            "out" if it["stock_qty"] <= 0
            else "low" if it["stock_qty"] <= it.get("min_stock", 0)
            else "ok"
        )
    return serialize_doc(items)


@router.post("/items")
async def create_item(request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    if not body.get("name"):
        raise HTTPException(400, "name wajib diisi")

    seq = (await db.acc_items.count_documents({"deleted": {"$ne": True}})) + 1
    code = body.get("code") or f"ACC-{str(seq).zfill(4)}"
    doc = {
        "id": _id(), "code": code, "name": body["name"],
        "category": body.get("category", "Umum"),
        "unit": body.get("unit", "pcs"),
        "description": body.get("description", ""),
        "min_stock": float(body.get("min_stock", 0)),
        "supplier": body.get("supplier", ""),
        "notes": body.get("notes", ""),
        "deleted": False,
        "created_by": user["name"], "created_at": _now(), "updated_at": _now()
    }
    await db.acc_items.insert_one(doc)
    doc["stock_qty"] = 0
    doc["stock_status"] = "out"
    return JSONResponse(serialize_doc(doc), status_code=201)


@router.put("/items/{item_id}")
async def update_item(item_id: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    existing = await db.acc_items.find_one({"id": item_id, "deleted": {"$ne": True}})
    if not existing:
        raise HTTPException(404, "Item tidak ditemukan")
    upd = {k: v for k, v in body.items() if k not in ("_id", "id", "created_at", "created_by")}
    upd["updated_at"] = _now()
    await db.acc_items.update_one({"id": item_id}, {"$set": upd})
    result = await db.acc_items.find_one({"id": item_id}, {"_id": 0})
    result["stock_qty"] = await _stock_qty(db, item_id)
    return serialize_doc(result)


@router.delete("/items/{item_id}")
async def delete_item(item_id: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    await db.acc_items.update_one({"id": item_id}, {"$set": {"deleted": True, "updated_at": _now()}})
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════
# STOK — MOVEMENTS & ADJUST
# ═══════════════════════════════════════════════════════════════

@router.get("/stock")
async def get_stock_overview(request: Request):
    user = await require_auth(request)
    db = get_db()
    items = await db.acc_items.find({"deleted": {"$ne": True}}, {"_id": 0}).sort("name", 1).to_list(500)
    stock_map = await _all_stock(db)
    result = []
    for it in items:
        qty = stock_map.get(it["id"], 0)
        result.append({
            "id": it["id"], "code": it["code"], "name": it["name"],
            "category": it["category"], "unit": it["unit"],
            "stock_qty": qty, "min_stock": it.get("min_stock", 0),
            "stock_status": ("out" if qty <= 0 else "low" if qty <= it.get("min_stock", 0) else "ok")
        })
    return serialize_doc(result)


@router.get("/stock/movements")
async def get_movements(request: Request):
    user = await require_auth(request)
    db = get_db()
    sp = request.query_params
    query = {}
    if sp.get("acc_id"):
        query["acc_id"] = sp["acc_id"]
    if sp.get("movement_type"):
        query["movement_type"] = sp["movement_type"]
    docs = await db.acc_stock_movements.find(query, {"_id": 0}).sort("created_at", -1).limit(200).to_list(500)
    return serialize_doc(docs)


@router.post("/stock/receive")
async def receive_stock(request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    acc_id = body.get("acc_id")
    qty = float(body.get("qty", 0))
    if not acc_id or qty <= 0:
        raise HTTPException(400, "acc_id dan qty > 0 wajib diisi")
    item = await db.acc_items.find_one({"id": acc_id, "deleted": {"$ne": True}})
    if not item:
        raise HTTPException(404, "Aksesoris tidak ditemukan")
    mv = {
        "id": _id(), "acc_id": acc_id, "acc_name": item["name"],
        "movement_type": "IN", "qty_signed": qty,
        "ref_type": body.get("ref_type", "manual"),
        "ref_id": body.get("ref_id", ""),
        "ref_number": body.get("ref_number", ""),
        "notes": body.get("notes", ""),
        "created_by": user["name"], "created_at": _now()
    }
    await db.acc_stock_movements.insert_one(mv)
    new_qty = await _stock_qty(db, acc_id)
    return JSONResponse({"ok": True, "new_qty": new_qty}, status_code=201)


@router.post("/stock/issue")
async def issue_stock(request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    acc_id = body.get("acc_id")
    qty = float(body.get("qty", 0))
    if not acc_id or qty <= 0:
        raise HTTPException(400, "acc_id dan qty > 0 wajib diisi")
    current = await _stock_qty(db, acc_id)
    if current < qty:
        raise HTTPException(400, f"Stok tidak cukup. Stok saat ini: {current}")
    item = await db.acc_items.find_one({"id": acc_id})
    mv = {
        "id": _id(), "acc_id": acc_id, "acc_name": item["name"] if item else "",
        "movement_type": "OUT", "qty_signed": -qty,
        "ref_type": body.get("ref_type", "manual"),
        "ref_id": body.get("ref_id", ""),
        "ref_number": body.get("ref_number", ""),
        "notes": body.get("notes", ""),
        "created_by": user["name"], "created_at": _now()
    }
    await db.acc_stock_movements.insert_one(mv)
    new_qty = await _stock_qty(db, acc_id)
    return JSONResponse({"ok": True, "new_qty": new_qty}, status_code=201)


# ═══════════════════════════════════════════════════════════════
# INTERNAL REQUESTS — Request dari Divisi Internal
# ═══════════════════════════════════════════════════════════════

DIVISI_OPTIONS = ["Produksi", "Cutting", "CMT", "Gudang", "Kantor", "SDM", "QC", "Packing", "Marketing", "Lainnya"]

@router.get("/internal-requests")
async def list_internal_requests(request: Request):
    user = await require_auth(request)
    db = get_db()
    sp = request.query_params
    query = {}
    if sp.get("status"):
        query["status"] = sp["status"]
    if sp.get("divisi"):
        query["divisi"] = sp["divisi"]
    docs = await db.acc_internal_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return serialize_doc(docs)


@router.post("/internal-requests")
async def create_internal_request(request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    if not body.get("divisi"):
        raise HTTPException(400, "divisi wajib diisi")
    if not body.get("items") or not isinstance(body["items"], list) or len(body["items"]) == 0:
        raise HTTPException(400, "items wajib diisi minimal 1")

    seq = (await db.acc_internal_requests.count_documents({})) + 1
    doc = {
        "id": _id(),
        "request_number": f"INT-REQ-{str(seq).zfill(4)}",
        "divisi": body["divisi"],
        "requester_name": body.get("requester_name", user["name"]),
        "purpose": body.get("purpose", ""),
        "needed_by": body.get("needed_by", ""),
        "items": body["items"],          # [{acc_id, acc_name, acc_code, qty_requested, unit, notes}]
        "status": "Pending",             # Pending | Approved | Rejected | Issued
        "admin_notes": "",
        "issued_by": "", "issued_at": "",
        "created_by": user["name"], "created_at": _now(), "updated_at": _now()
    }
    await db.acc_internal_requests.insert_one(doc)
    return JSONResponse(serialize_doc(doc), status_code=201)


@router.put("/internal-requests/{req_id}")
async def update_internal_request(req_id: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    doc = await db.acc_internal_requests.find_one({"id": req_id})
    if not doc:
        raise HTTPException(404, "Request tidak ditemukan")

    new_status = body.get("status")
    upd = {"updated_at": _now()}

    if new_status == "Approved":
        upd.update({"status": "Approved", "admin_notes": body.get("admin_notes", ""),
                     "approved_by": user["name"], "approved_at": _now()})

    elif new_status == "Rejected":
        upd.update({"status": "Rejected", "admin_notes": body.get("admin_notes", ""),
                     "rejected_by": user["name"], "rejected_at": _now()})

    elif new_status == "Issued":
        # Kurangi stok untuk setiap item
        for it in doc.get("items", []):
            acc_id = it.get("acc_id")
            qty = float(it.get("qty_requested", 0))
            if acc_id and qty > 0:
                current = await _stock_qty(db, acc_id)
                item_doc = await db.acc_items.find_one({"id": acc_id})
                mv = {
                    "id": _id(), "acc_id": acc_id,
                    "acc_name": item_doc["name"] if item_doc else it.get("acc_name", ""),
                    "movement_type": "OUT", "qty_signed": -qty,
                    "ref_type": "internal_request", "ref_id": req_id,
                    "ref_number": doc["request_number"],
                    "notes": f"Issued ke {doc['divisi']}",
                    "created_by": user["name"], "created_at": _now()
                }
                await db.acc_stock_movements.insert_one(mv)
        upd.update({"status": "Issued", "issued_by": user["name"], "issued_at": _now()})

    else:
        allowed = {k: v for k, v in body.items() if k not in ("_id", "id", "created_at", "created_by", "request_number")}
        upd.update(allowed)

    await db.acc_internal_requests.update_one({"id": req_id}, {"$set": upd})
    result = await db.acc_internal_requests.find_one({"id": req_id}, {"_id": 0})
    return serialize_doc(result)


# ═══════════════════════════════════════════════════════════════
# PEMINJAMAN AKSESORIS
# ═══════════════════════════════════════════════════════════════

@router.get("/loans")
async def list_loans(request: Request):
    user = await require_auth(request)
    db = get_db()
    sp = request.query_params
    query = {}
    if sp.get("status"):
        query["status"] = sp["status"]
    docs = await db.acc_loans.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return serialize_doc(docs)


@router.post("/loans")
async def create_loan(request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    if not body.get("borrower_name"):
        raise HTTPException(400, "borrower_name wajib diisi")
    if not body.get("items") or len(body["items"]) == 0:
        raise HTTPException(400, "items wajib diisi")

    # Cek & kurangi stok
    for it in body["items"]:
        acc_id = it.get("acc_id")
        qty = float(it.get("qty", 0))
        if acc_id and qty > 0:
            current = await _stock_qty(db, acc_id)
            if current < qty:
                item_doc = await db.acc_items.find_one({"id": acc_id})
                name = item_doc["name"] if item_doc else acc_id
                raise HTTPException(400, f"Stok {name} tidak cukup (ada: {current}, diminta: {qty})")

    seq = (await db.acc_loans.count_documents({})) + 1
    doc = {
        "id": _id(),
        "loan_number": f"LOAN-{str(seq).zfill(4)}",
        "borrower_name": body["borrower_name"],
        "borrower_divisi": body.get("borrower_divisi", ""),
        "purpose": body.get("purpose", ""),
        "loan_date": body.get("loan_date", _now()[:10]),
        "expected_return_date": body.get("expected_return_date", ""),
        "items": body["items"],    # [{acc_id, acc_name, qty, unit}]
        "status": "Active",        # Active | Returned | Overdue
        "return_notes": "",
        "returned_at": "",
        "created_by": user["name"], "created_at": _now(), "updated_at": _now()
    }
    await db.acc_loans.insert_one(doc)

    # Kurangi stok
    for it in body["items"]:
        acc_id = it.get("acc_id")
        qty = float(it.get("qty", 0))
        if acc_id and qty > 0:
            item_doc = await db.acc_items.find_one({"id": acc_id})
            mv = {
                "id": _id(), "acc_id": acc_id,
                "acc_name": item_doc["name"] if item_doc else it.get("acc_name", ""),
                "movement_type": "LOAN_OUT", "qty_signed": -qty,
                "ref_type": "loan", "ref_id": doc["id"],
                "ref_number": doc["loan_number"],
                "notes": f"Dipinjam oleh {body['borrower_name']}",
                "created_by": user["name"], "created_at": _now()
            }
            await db.acc_stock_movements.insert_one(mv)

    return JSONResponse(serialize_doc(doc), status_code=201)


@router.put("/loans/{loan_id}/return")
async def return_loan(loan_id: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    loan = await db.acc_loans.find_one({"id": loan_id})
    if not loan:
        raise HTTPException(404, "Peminjaman tidak ditemukan")
    if loan["status"] != "Active":
        raise HTTPException(400, "Peminjaman sudah dikembalikan")

    # Kembalikan stok
    for it in loan.get("items", []):
        acc_id = it.get("acc_id")
        qty = float(it.get("qty", 0))
        if acc_id and qty > 0:
            item_doc = await db.acc_items.find_one({"id": acc_id})
            mv = {
                "id": _id(), "acc_id": acc_id,
                "acc_name": item_doc["name"] if item_doc else it.get("acc_name", ""),
                "movement_type": "LOAN_RETURN", "qty_signed": qty,
                "ref_type": "loan", "ref_id": loan_id,
                "ref_number": loan["loan_number"],
                "notes": f"Dikembalikan oleh {loan['borrower_name']}",
                "created_by": user["name"], "created_at": _now()
            }
            await db.acc_stock_movements.insert_one(mv)

    await db.acc_loans.update_one({"id": loan_id}, {"$set": {
        "status": "Returned",
        "return_notes": body.get("return_notes", ""),
        "returned_at": _now(),
        "returned_by": user["name"],
        "updated_at": _now()
    }})
    result = await db.acc_loans.find_one({"id": loan_id}, {"_id": 0})
    return serialize_doc(result)


# ═══════════════════════════════════════════════════════════════
# STOK OPNAME
# ═══════════════════════════════════════════════════════════════

@router.get("/opname")
async def list_opname(request: Request):
    user = await require_auth(request)
    db = get_db()
    sessions = await db.acc_opname_sessions.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return serialize_doc(sessions)


@router.post("/opname")
async def start_opname(request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()

    # Cek ada sesi aktif
    active = await db.acc_opname_sessions.find_one({"status": "Active"})
    if active:
        raise HTTPException(400, f"Masih ada sesi opname aktif: {active.get('ref_number')}")

    seq = (await db.acc_opname_sessions.count_documents({})) + 1
    session_id = _id()
    ref = f"OPNAME-{str(seq).zfill(4)}"

    # Snapshot semua aksesoris dengan stok sistem
    items = await db.acc_items.find({"deleted": {"$ne": True}}, {"_id": 0}).to_list(500)
    stock_map = await _all_stock(db)
    lines = []
    for it in items:
        lines.append({
            "id": _id(), "session_id": session_id,
            "acc_id": it["id"], "acc_name": it["name"], "acc_code": it["code"],
            "unit": it["unit"],
            "system_qty": stock_map.get(it["id"], 0),
            "counted_qty": None,  # belum dihitung
            "diff": None,
            "notes": ""
        })

    session = {
        "id": session_id, "ref_number": ref,
        "notes": body.get("notes", ""),
        "status": "Active",
        "total_items": len(lines), "counted_items": 0,
        "started_by": user["name"], "started_at": _now(),
        "completed_at": "", "completed_by": "",
        "created_at": _now(), "updated_at": _now()
    }
    await db.acc_opname_sessions.insert_one(session)
    if lines:
        await db.acc_opname_lines.insert_many(lines)

    session["lines"] = lines
    return JSONResponse(serialize_doc(session), status_code=201)


@router.get("/opname/{session_id}")
async def get_opname_detail(session_id: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    session = await db.acc_opname_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(404, "Sesi tidak ditemukan")
    lines = await db.acc_opname_lines.find({"session_id": session_id}, {"_id": 0}).to_list(500)
    session["lines"] = lines
    return serialize_doc(session)


@router.put("/opname/{session_id}/count")
async def update_count(session_id: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    # body: {acc_id, counted_qty, notes}
    acc_id = body.get("acc_id")
    counted_qty = body.get("counted_qty")
    if acc_id is None or counted_qty is None:
        raise HTTPException(400, "acc_id dan counted_qty wajib diisi")

    line = await db.acc_opname_lines.find_one({"session_id": session_id, "acc_id": acc_id})
    if not line:
        raise HTTPException(404, "Baris opname tidak ditemukan")

    system_qty = line.get("system_qty", 0)
    diff = float(counted_qty) - float(system_qty)
    await db.acc_opname_lines.update_one(
        {"session_id": session_id, "acc_id": acc_id},
        {"$set": {"counted_qty": float(counted_qty), "diff": diff,
                  "notes": body.get("notes", ""),
                  "counted_by": user["name"], "counted_at": _now()}}
    )

    # Update counted_items di session
    total_counted = await db.acc_opname_lines.count_documents(
        {"session_id": session_id, "counted_qty": {"$ne": None}})
    await db.acc_opname_sessions.update_one(
        {"id": session_id},
        {"$set": {"counted_items": total_counted, "updated_at": _now()}}
    )
    return {"ok": True, "diff": diff}


@router.post("/opname/{session_id}/complete")
async def complete_opname(session_id: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    session = await db.acc_opname_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(404, "Sesi tidak ditemukan")
    if session["status"] != "Active":
        raise HTTPException(400, "Sesi sudah selesai atau dibatalkan")

    lines = await db.acc_opname_lines.find(
        {"session_id": session_id, "diff": {"$nin": [None, 0]}},
        {"_id": 0}
    ).to_list(500)

    # Buat adjustment movements untuk setiap selisih
    for ln in lines:
        diff = float(ln.get("diff", 0))
        if diff != 0:
            mv = {
                "id": _id(), "acc_id": ln["acc_id"], "acc_name": ln["acc_name"],
                "movement_type": "ADJUST",
                "qty_signed": diff,
                "ref_type": "opname", "ref_id": session_id,
                "ref_number": session["ref_number"],
                "notes": f"Adjustment opname {session['ref_number']}",
                "created_by": user["name"], "created_at": _now()
            }
            await db.acc_stock_movements.insert_one(mv)

    await db.acc_opname_sessions.update_one({"id": session_id}, {"$set": {
        "status": "Completed",
        "completed_by": user["name"], "completed_at": _now(), "updated_at": _now()
    }})
    return {"ok": True, "adjustments_made": len(lines)}


@router.post("/opname/{session_id}/cancel")
async def cancel_opname(session_id: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    await db.acc_opname_sessions.update_one({"id": session_id}, {"$set": {
        "status": "Cancelled", "updated_at": _now()
    }})
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════
# PURCHASE REQUEST KE FINANCE
# ═══════════════════════════════════════════════════════════════

@router.get("/purchase-requests")
async def list_purchase_requests(request: Request):
    user = await require_auth(request)
    db = get_db()
    sp = request.query_params
    query = {}
    if sp.get("status"):
        query["status"] = sp["status"]
    docs = await db.acc_purchase_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return serialize_doc(docs)


@router.post("/purchase-requests")
async def create_purchase_request(request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    if not body.get("items") or len(body["items"]) == 0:
        raise HTTPException(400, "items wajib diisi")

    seq = (await db.acc_purchase_requests.count_documents({})) + 1
    doc = {
        "id": _id(),
        "pr_number": f"ACC-PR-{str(seq).zfill(4)}",
        "priority": body.get("priority", "Normal"),   # Urgent | Normal | Low
        "purpose": body.get("purpose", ""),
        "supplier": body.get("supplier", ""),
        "items": body["items"],   # [{acc_id, acc_name, qty_requested, unit, estimated_price, notes}]
        "total_estimated": sum(
            float(i.get("qty_requested", 0)) * float(i.get("estimated_price", 0))
            for i in body["items"]
        ),
        "notes": body.get("notes", ""),
        "status": "Draft",   # Draft | Submitted | Approved | Rejected | Ordered | Received
        "submitted_at": "",
        "approved_by": "", "approved_at": "",
        "finance_notes": "",
        "created_by": user["name"], "created_at": _now(), "updated_at": _now()
    }
    await db.acc_purchase_requests.insert_one(doc)
    return JSONResponse(serialize_doc(doc), status_code=201)


@router.put("/purchase-requests/{pr_id}")
async def update_purchase_request(pr_id: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    doc = await db.acc_purchase_requests.find_one({"id": pr_id})
    if not doc:
        raise HTTPException(404, "PR tidak ditemukan")

    new_status = body.get("status")
    upd = {"updated_at": _now()}

    if new_status == "Submitted":
        upd.update({"status": "Submitted", "submitted_at": _now()})
    elif new_status == "Approved":
        upd.update({"status": "Approved", "approved_by": user["name"],
                     "approved_at": _now(), "finance_notes": body.get("finance_notes", "")})
    elif new_status == "Rejected":
        upd.update({"status": "Rejected", "finance_notes": body.get("finance_notes", ""),
                     "rejected_by": user["name"], "rejected_at": _now()})
    elif new_status == "Ordered":
        upd.update({"status": "Ordered", "ordered_at": _now()})
    elif new_status == "Received":
        # Auto-receive stok ke gudang aksesoris
        for it in doc.get("items", []):
            acc_id = it.get("acc_id")
            qty = float(it.get("qty_requested", 0))
            if acc_id and qty > 0:
                item_doc = await db.acc_items.find_one({"id": acc_id})
                mv = {
                    "id": _id(), "acc_id": acc_id,
                    "acc_name": item_doc["name"] if item_doc else it.get("acc_name", ""),
                    "movement_type": "IN",
                    "qty_signed": qty,
                    "ref_type": "purchase_request", "ref_id": pr_id,
                    "ref_number": doc["pr_number"],
                    "notes": f"Terima dari PR {doc['pr_number']}",
                    "created_by": user["name"], "created_at": _now()
                }
                await db.acc_stock_movements.insert_one(mv)
        upd.update({"status": "Received", "received_at": _now()})
    else:
        allowed = {k: v for k, v in body.items() if k not in ("_id", "id", "created_at", "created_by", "pr_number")}
        upd.update(allowed)

    await db.acc_purchase_requests.update_one({"id": pr_id}, {"$set": upd})
    result = await db.acc_purchase_requests.find_one({"id": pr_id}, {"_id": 0})
    return serialize_doc(result)


# ═══════════════════════════════════════════════════════════════
# DASHBOARD SUMMARY
# ═══════════════════════════════════════════════════════════════

@router.get("/dashboard")
async def get_dashboard(request: Request):
    user = await require_auth(request)
    db = get_db()

    total_items = await db.acc_items.count_documents({"deleted": {"$ne": True}})
    stock_map = await _all_stock(db)
    items = await db.acc_items.find({"deleted": {"$ne": True}}, {"_id": 0}).to_list(500)

    low_stock_items = []
    out_of_stock = 0
    low_stock = 0
    for it in items:
        qty = stock_map.get(it["id"], 0)
        if qty <= 0:
            out_of_stock += 1
        elif qty <= it.get("min_stock", 0) and it.get("min_stock", 0) > 0:
            low_stock += 1
            low_stock_items.append({"id": it["id"], "code": it["code"], "name": it["name"],
                                     "stock_qty": qty, "min_stock": it.get("min_stock", 0), "unit": it["unit"]})

    pending_requests = await db.acc_internal_requests.count_documents({"status": "Pending"})
    active_loans = await db.acc_loans.count_documents({"status": "Active"})
    pending_pr = await db.acc_purchase_requests.count_documents({"status": {"$in": ["Draft", "Submitted"]}})
    active_opname = await db.acc_opname_sessions.find_one({"status": "Active"})

    return {
        "total_items": total_items,
        "out_of_stock": out_of_stock,
        "low_stock": low_stock,
        "low_stock_items": low_stock_items[:5],
        "pending_requests": pending_requests,
        "active_loans": active_loans,
        "pending_pr": pending_pr,
        "active_opname": active_opname["ref_number"] if active_opname else None
    }
