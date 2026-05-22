"""
Portal Saya — HR Self-Service Endpoints
========================================
Endpoint untuk karyawan melihat data HR mereka sendiri.
Resolves user_id dari JWT → rahaza_employee (via user_id link atau email fallback).

Endpoints:
  GET /api/portal-saya/me/employee     — profil karyawan saya
  GET /api/portal-saya/me/payslips     — slip gaji saya (list + detail)
  GET /api/portal-saya/me/leaves       — riwayat cuti/izin saya
  GET /api/portal-saya/me/leave-balance — saldo cuti saya
"""
from fastapi import APIRouter, HTTPException, Request, Query
from database import get_db
from auth import require_auth, serialize_doc
from typing import Optional
import logging

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/portal-saya/me", tags=["portal-saya-hr"])


async def _get_my_employee(db, user: dict):
    """
    Resolve user → employee. Coba:
      1. rahaza_employees.user_id == user.id
      2. rahaza_employees.email == user.email (fallback)
    Returns employee doc or raises 404.
    """
    uid   = user.get("id")
    email = (user.get("email") or "").lower()

    emp = await db.rahaza_employees.find_one(
        {"user_id": uid, "active": True}, {"_id": 0}
    )
    if emp:
        return emp

    if email:
        emp = await db.rahaza_employees.find_one(
            {"email": email, "active": True}, {"_id": 0}
        )
        if emp:
            return emp

    raise HTTPException(
        404,
        "Data karyawan Anda belum terdaftar atau belum ditautkan ke akun ini. "
        "Hubungi HR untuk melakukan penautkan akun."
    )


# ── GET /me/employee ──────────────────────────────────────────────────────────

@router.get("/employee")
async def my_employee_profile(request: Request):
    """Profil karyawan berdasarkan JWT user."""
    user = await require_auth(request)
    db   = get_db()
    emp  = await _get_my_employee(db, user)
    # Exclude sensitive fields for self-service
    safe_fields = {
        "id", "employee_code", "name", "department", "job_title", "email", "phone",
        "contract_type", "contract_start_date", "contract_end_date", "wage_scheme",
        "joined_at", "gender", "birth_date", "marital_status", "religion",
        "photo_url", "grade", "active", "manager_id", "manager_name",
        "bank_name", "bank_account_number", "bank_account_holder",
        "bpjs_kesehatan_number", "bpjs_ketenagakerjaan_number",
        "user_id", "user_email",
    }
    return serialize_doc({k: v for k, v in emp.items() if k in safe_fields})


# ── GET /me/payslips ──────────────────────────────────────────────────────────

@router.get("/payslips")
async def my_payslips(
    request: Request,
    limit: int = Query(12, ge=1, le=36),
):
    """List slip gaji saya (terbaru dulu, maks 12 bulan)."""
    user = await require_auth(request)
    db   = get_db()
    emp  = await _get_my_employee(db, user)

    # Fetch payslips dari rahaza_payroll_runs (payslips embedded) atau payslip collection
    # Pattern: payslips disimpan dalam rahaza_payroll_runs.payslips[] atau koleksi terpisah
    # Cek dua kemungkinan penyimpanan
    payslips = []

    # Option A: payslips dalam runs (embedded)
    runs = await db.rahaza_payroll_runs.find(
        {"status": {"$ne": "cancelled"}},
        {"_id": 0, "id": 1, "run_number": 1, "period_from": 1, "period_to": 1,
         "status": 1, "finalized_at": 1, "payslips": 1}
    ).sort("period_from", -1).limit(limit).to_list(limit)

    for run in runs:
        for ps in (run.get("payslips") or []):
            if ps.get("employee_id") == emp["id"]:
                payslips.append({
                    **ps,
                    "run_id":     run["id"],
                    "run_number": run.get("run_number"),
                    "run_status": run.get("status"),
                    "period_from": run.get("period_from"),
                    "period_to":   run.get("period_to"),
                    "finalized_at": run.get("finalized_at"),
                })

    if not payslips:
        # Option B: payslips dalam koleksi terpisah (rahaza_payslips)
        raw = await db.rahaza_payslips.find(
            {"employee_id": emp["id"]}, {"_id": 0}
        ).sort("period_from", -1).limit(limit).to_list(limit)
        payslips = serialize_doc(raw)

    return serialize_doc({
        "employee_code": emp.get("employee_code"),
        "employee_name": emp.get("name"),
        "total":         len(payslips),
        "payslips":      payslips,
    })


# ── GET /me/leaves ────────────────────────────────────────────────────────────

@router.get("/leaves")
async def my_leaves(
    request: Request,
    status:  Optional[str] = Query(None),
    year:    Optional[int]  = Query(None),
    limit:   int            = Query(50, ge=1, le=200),
):
    """Riwayat cuti/izin saya."""
    user = await require_auth(request)
    db   = get_db()
    emp  = await _get_my_employee(db, user)

    q: dict = {"employee_id": emp["id"]}
    if status:
        q["status"] = status
    if year:
        q["from_date"] = {"$regex": f"^{year}"}

    rows = await db.rahaza_leave_requests.find(
        q, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)

    # Enrich with leave type names
    lt_ids = list({r.get("leave_type_id") for r in rows if r.get("leave_type_id")})
    lt_map = {}
    if lt_ids:
        async for lt in db.rahaza_leave_types.find({"id": {"$in": lt_ids}}, {"_id": 0}):
            lt_map[lt["id"]] = lt
    for r in rows:
        lt = lt_map.get(r.get("leave_type_id")) or {}
        r["leave_type_name"] = lt.get("name")
        r["leave_type_code"] = lt.get("code")
        r["is_paid"]         = lt.get("paid", True)

    return serialize_doc({"employee_id": emp["id"], "total": len(rows), "items": rows})


# ── GET /me/leave-balance ──────────────────────────────────────────────────────

@router.get("/leave-balance")
async def my_leave_balance(
    request: Request,
    year: Optional[int] = Query(None),
):
    """Saldo cuti saya per tipe."""
    from datetime import datetime
    user = await require_auth(request)
    db   = get_db()
    emp  = await _get_my_employee(db, user)
    y    = year or datetime.now().year

    leave_types = await db.rahaza_leave_types.find(
        {"active": True}, {"_id": 0}
    ).to_list(500)

    # Compute used from approved leaves
    leaves = await db.rahaza_leave_requests.find({
        "employee_id": emp["id"],
        "status":      "approved",
        "from_date":   {"$regex": f"^{y}"},
    }, {"_id": 0, "leave_type_id": 1, "duration_working_days": 1, "duration_days": 1}).to_list(500)

    used_map: dict = {}
    for lv in leaves:
        lt_id = lv.get("leave_type_id")
        days  = float(lv.get("duration_working_days") or lv.get("duration_days") or 0)
        used_map[lt_id] = used_map.get(lt_id, 0) + days

    balances = []
    for lt in leave_types:
        quota     = lt.get("quota_default", 0)
        used      = used_map.get(lt["id"], 0)
        remaining = max(0, quota - used)
        balances.append({
            "leave_type_id":   lt["id"],
            "leave_type_code": lt.get("code"),
            "leave_type_name": lt.get("name"),
            "request_type":    lt.get("request_type", "cuti"),
            "quota":           quota,
            "used":            used,
            "remaining":       remaining,
            "is_paid":         lt.get("paid", True),
            "unpaid":          lt.get("unpaid", False),
        })

    return serialize_doc({
        "employee_id":   emp["id"],
        "employee_name": emp.get("name"),
        "year":          y,
        "balances":      [b for b in balances if b["quota"] > 0],
    })
