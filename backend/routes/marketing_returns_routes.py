"""
Returns & Refunds Tracking Module — Backend Routes
Phase 3 Week 13: Tracking retur dan refund produk
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel
from database import get_db
from auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/marketing/returns", tags=["marketing-returns"])

RETURN_REASONS = [
    "produk_tidak_sesuai",
    "ukuran_salah",
    "produk_cacat",
    "warna_berbeda",
    "tidak_sesuai_ekspektasi",
    "salah_pesan",
    "terlambat_sampai",
    "rusak_saat_pengiriman",
    "lainnya"
]

REASON_LABELS = {
    "produk_tidak_sesuai": "Produk Tidak Sesuai Deskripsi",
    "ukuran_salah": "Ukuran Salah/Tidak Sesuai",
    "produk_cacat": "Produk Cacat/Rusak",
    "warna_berbeda": "Warna Berbeda dari Gambar",
    "tidak_sesuai_ekspektasi": "Tidak Sesuai Ekspektasi",
    "salah_pesan": "Salah Pesan",
    "terlambat_sampai": "Terlambat Sampai",
    "rusak_saat_pengiriman": "Rusak Saat Pengiriman",
    "lainnya": "Lainnya"
}

RETURN_STATUSES = ["pending", "approved", "rejected", "completed", "cancelled"]
REFUND_TYPES = ["full_refund", "partial_refund", "exchange", "no_refund"]
PLATFORMS = ["shopee", "tiktok", "tokopedia", "instagram"]
COURIERS = ["jnt", "spx", "sicepat", "jne", "anteraja", "ninja", "grab", "gojek"]

# ── Helpers ───────────────────────────────────────────────────────────────────
def _now() -> datetime:
    return datetime.now(timezone.utc)

def serialize(obj):
    if isinstance(obj, list):     return [serialize(i) for i in obj]
    if isinstance(obj, dict):     return {k: serialize(v) for k, v in obj.items() if k != "_id"}
    if isinstance(obj, datetime): return obj.isoformat()
    return obj

def _get_user(request: Request) -> dict:
    return getattr(request.state, "user", {}) or {}

# ── Seed ─────────────────────────────────────────────────────────────────────
async def seed_returns_if_empty():
    db = get_db()
    if await db.marketing_returns.count_documents({}) > 0:
        return

    import random
    
    products = [
        "Gamis Daluna Basic", "Khimar Syari Premium", "Tunik Busui Friendly",
        "Set Gamis + Khimar", "Outer Cardigan", "Rok Plisket Panjang"
    ]
    
    platforms_list = ["shopee", "tiktok", "tokopedia"]
    couriers_list = ["jnt", "spx", "sicepat"]
    
    return_templates = [
        {"reason": "ukuran_salah", "detail": "Terlalu kecil, size XL seperti M", "price": 125000},
        {"reason": "produk_tidak_sesuai", "detail": "Warna berbeda dari foto", "price": 98000},
        {"reason": "produk_cacat", "detail": "Ada bolong di bagian jahitan", "price": 150000},
        {"reason": "warna_berbeda", "detail": "Lebih gelap dari gambar", "price": 89000},
        {"reason": "tidak_sesuai_ekspektasi", "detail": "Bahan lebih tipis dari yang diharapkan", "price": 110000},
    ]
    
    # Gunakan platform accounts nyata jika ada
    real_accounts = await db.marketing_platform_accounts.find(
        {"status": "active"}, {"_id": 0, "id": 1, "account_name": 1, "platform": 1}
    ).to_list(50)
    seed_accounts = [(a["id"], a["account_name"], a["platform"]) for a in real_accounts] if real_accounts else [
        (None, "DA Official Shopee", "shopee"), (None, "Daluna TikTok Shop", "tiktok")
    ]

    entries = []
    base = _now()
    
    for i in range(30):
        day_offset = random.randint(-30, 0)
        return_date = base + timedelta(days=day_offset)
        
        template = random.choice(return_templates)
        status = random.choice(["pending", "approved", "approved", "completed", "rejected"])
        refund_type = random.choice(["full_refund", "partial_refund", "exchange"]) if status == "approved" else "no_refund"
        acc_id, acc_name, acc_platform = random.choice(seed_accounts)
        
        entries.append({
            "id": str(uuid.uuid4()),
            "date": return_date.date().isoformat(),
            "order_id": f"ORD-{random.randint(100000, 999999)}",
            "platform": acc_platform,
            "account_id": acc_id,
            "account_name": acc_name,
            "product": random.choice(products),
            "price": template["price"],
            "reason": template["reason"],
            "reason_label": REASON_LABELS.get(template["reason"], template["reason"]),
            "reason_detail": template["detail"],
            "courier": random.choice(couriers_list),
            "status": status,
            "refund_type": refund_type,
            "refund_amount": template["price"] if refund_type == "full_refund" else (template["price"] * 0.7) if refund_type == "partial_refund" else 0,
            "appeal_status": "accepted" if status == "approved" else "rejected" if status == "rejected" else "pending",
            "appeal_result": "Disetujui" if status == "approved" else "Ditolak" if status == "rejected" else "Menunggu",
            "notes": "",
            "created_by": "system",
            "created_at": _now(),
            "updated_at": _now(),
        })
    
    if entries:
        await db.marketing_returns.insert_many(entries)
    logger.info(f"[marketing_returns] seeded {len(entries)} entries")

# ── Models ───────────────────────────────────────────────────────────────────
class ReturnIn(BaseModel):
    account_id: Optional[str] = None  # UUID dari marketing_platform_accounts
    account_name: Optional[str] = None
    date: str
    order_id: str
    platform: str
    product: str
    price: float
    reason: str
    reason_detail: str
    courier: str
    refund_type: Optional[str] = "full_refund"
    notes: Optional[str] = ""

class ReturnUpdate(BaseModel):
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    date: Optional[str] = None
    order_id: Optional[str] = None
    platform: Optional[str] = None
    product: Optional[str] = None
    price: Optional[float] = None
    reason: Optional[str] = None
    reason_detail: Optional[str] = None
    courier: Optional[str] = None
    status: Optional[str] = None
    refund_type: Optional[str] = None
    refund_amount: Optional[float] = None
    appeal_status: Optional[str] = None
    appeal_result: Optional[str] = None
    notes: Optional[str] = None

# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/reasons")
async def get_reasons():
    return {"success": True, "reasons": [{"value": k, "label": v} for k, v in REASON_LABELS.items()]}

@router.get("/summary")
async def get_summary(request: Request):
    await require_auth(request)
    await seed_returns_if_empty()
    db = get_db()

    total = await db.marketing_returns.count_documents({})
    pending = await db.marketing_returns.count_documents({"status": "pending"})
    approved = await db.marketing_returns.count_documents({"status": "approved"})
    completed = await db.marketing_returns.count_documents({"status": "completed"})
    rejected = await db.marketing_returns.count_documents({"status": "rejected"})
    
    # Total refund amount
    pipeline_refund = [{"$group": {"_id": None, "total_refund": {"$sum": "$refund_amount"}}}]
    refund_result = await db.marketing_returns.aggregate(pipeline_refund).to_list(1)
    total_refund = refund_result[0]["total_refund"] if refund_result else 0
    
    # By reason
    pipeline_reason = [{"$group": {"_id": "$reason", "count": {"$sum": 1}}}]
    by_reason_raw = await db.marketing_returns.aggregate(pipeline_reason).to_list(100)
    by_reason = {REASON_LABELS.get(r["_id"], r["_id"]): r["count"] for r in by_reason_raw if r["_id"]}

    return {
        "success": True,
        "data": {
            "total": total,
            "pending": pending,
            "approved": approved,
            "completed": completed,
            "rejected": rejected,
            "total_refund": total_refund,
            "by_reason": by_reason,
        }
    }

@router.get("")
async def list_returns(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, le=100),
    status: str = Query(default=""),
    platform: str = Query(default=""),
    reason: str = Query(default=""),
    date_from: str = Query(default=""),
    date_to: str = Query(default=""),
    search: str = Query(default=""),
    account_id: str = Query(default=""),
):
    await require_auth(request)
    await seed_returns_if_empty()
    db = get_db()

    q = {}
    if status: q["status"] = status
    if platform: q["platform"] = platform
    if reason: q["reason"] = reason
    if date_from: q.setdefault("date", {})["$gte"] = date_from
    if date_to: q.setdefault("date", {})["$lte"] = date_to
    if account_id: q["account_id"] = account_id
    if search:
        q["$or"] = [
            {"order_id": {"$regex": search, "$options": "i"}},
            {"product": {"$regex": search, "$options": "i"}},
            {"reason_detail": {"$regex": search, "$options": "i"}},
        ]

    total = await db.marketing_returns.count_documents(q)
    skip = (page - 1) * page_size
    items = await db.marketing_returns.find(q, {"_id": 0})\
                    .sort("date", -1).skip(skip).limit(page_size).to_list(page_size)
    
    return {
        "success": True,
        "data": serialize(items),
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    }

@router.get("/{return_id}")
async def get_return(return_id: str, request: Request):
    await require_auth(request)
    db = get_db()
    ret = await db.marketing_returns.find_one({"id": return_id}, {"_id": 0})
    if not ret:
        raise HTTPException(404, "Return not found")
    return {"success": True, "data": serialize(ret)}

@router.post("")
async def create_return(body: ReturnIn, request: Request):
    await require_auth(request)
    user = _get_user(request)
    db = get_db()

    refund_amount = body.price if body.refund_type == "full_refund" else (body.price * 0.7) if body.refund_type == "partial_refund" else 0

    ret = {
        "id": str(uuid.uuid4()),
        "account_id": body.account_id,  # FK to marketing_platform_accounts
        "account_name": body.account_name,  # Denormalized for display
        "date": body.date,
        "order_id": body.order_id,
        "platform": body.platform,
        "product": body.product,
        "price": body.price,
        "reason": body.reason,
        "reason_label": REASON_LABELS.get(body.reason, body.reason),
        "reason_detail": body.reason_detail,
        "courier": body.courier,
        "status": "pending",
        "refund_type": body.refund_type,
        "refund_amount": refund_amount,
        "appeal_status": "pending",
        "appeal_result": "Menunggu",
        "notes": body.notes or "",
        "created_by": user.get("email", "unknown"),
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db.marketing_returns.insert_one(ret)
    return {"success": True, "data": serialize(ret)}

@router.put("/{return_id}")
async def update_return(return_id: str, body: ReturnUpdate, request: Request):
    await require_auth(request)
    db = get_db()

    existing = await db.marketing_returns.find_one({"id": return_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Return not found")

    upd = {k: v for k, v in body.dict().items() if v is not None}
    if "reason" in upd:
        upd["reason_label"] = REASON_LABELS.get(upd["reason"], upd["reason"])
    upd["updated_at"] = _now()
    
    await db.marketing_returns.update_one({"id": return_id}, {"$set": upd})
    updated = {**existing, **upd}
    return {"success": True, "data": serialize(updated)}

@router.delete("/{return_id}")
async def delete_return(return_id: str, request: Request):
    await require_auth(request)
    db = get_db()
    res = await db.marketing_returns.delete_one({"id": return_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Return not found")
    return {"success": True, "message": "Deleted"}

@router.post("/{return_id}/approve")
async def approve_return(return_id: str, request: Request):
    await require_auth(request)
    db = get_db()
    existing = await db.marketing_returns.find_one({"id": return_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Return not found")
    
    await db.marketing_returns.update_one(
        {"id": return_id},
        {"$set": {
            "status": "approved",
            "appeal_status": "accepted",
            "appeal_result": "Disetujui",
            "updated_at": _now()
        }}
    )
    return {"success": True, "message": "Return approved"}

@router.post("/{return_id}/reject")
async def reject_return(return_id: str, request: Request):
    await require_auth(request)
    body = await request.json()
    notes = body.get("notes", "")
    
    db = get_db()
    existing = await db.marketing_returns.find_one({"id": return_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Return not found")
    
    await db.marketing_returns.update_one(
        {"id": return_id},
        {"$set": {
            "status": "rejected",
            "appeal_status": "rejected",
            "appeal_result": "Ditolak",
            "refund_amount": 0,
            "notes": notes,
            "updated_at": _now()
        }}
    )
    return {"success": True, "message": "Return rejected"}

@router.post("/{return_id}/complete")
async def complete_return(return_id: str, request: Request):
    await require_auth(request)
    db = get_db()
    existing = await db.marketing_returns.find_one({"id": return_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Return not found")
    if existing.get("status") != "approved":
        raise HTTPException(400, "Only approved returns can be completed")
    
    await db.marketing_returns.update_one(
        {"id": return_id},
        {"$set": {
            "status": "completed",
            "updated_at": _now()
        }}
    )
    return {"success": True, "message": "Return completed"}
