"""
PT Rahaza / CV. Dewi Aditya — Payroll (Fase 8b + 8c + 8d DA)

Fase 8b — Payroll Profiles per Pegawai
Fase 8c — Payroll Run & Payslip
Fase 8d — DA Allowance Templates (tunjangan tetap yang bisa dikonfigurasi)

  - /payroll-allowances               (GET list, POST create)
  - /payroll-allowances/{id}          (PUT, DELETE)
  - /payroll-allowances/apply-to-run  (POST: apply allowances to a run's payslips)
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from database import get_db
from auth import require_auth, serialize_doc, log_activity
import uuid
import io
import csv
import logging
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from routes.rahaza_posting import post_payroll_run
from utils.saga import SagaExecutor

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rahaza", tags=["rahaza-payroll"])

VALID_SCHEMES = ["pcs", "hourly", "weekly", "monthly"]
VALID_PERIOD_TYPES = ["weekly", "monthly"]
VALID_RUN_STATUS = ["draft", "finalized", "cancelled"]


def _uid(): return str(uuid.uuid4())
def _now(): return datetime.now(timezone.utc)


# ─── ALLOWANCE HELPERS ────────────────────────────────────────────────────────

async def _get_applicable_allowances(db, employee: dict) -> list:
    """
    Ambil semua tunjangan tetap yang berlaku untuk karyawan ini.
    applicable_to: 'all' | 'department' | 'employee'
    """
    emp_id = employee.get("id") or employee.get("employee_id")
    dept = employee.get("department") or ""
    employee.get("employee_code") or ""

    all_templates = await db.da_payroll_allowances.find(
        {"is_active": True}, {"_id": 0}
    ).to_list(500)

    applicable = []
    for t in all_templates:
        scope = t.get("applicable_to", "all")
        if scope == "all":
            applicable.append(t)
        elif scope == "department" and dept and t.get("department") == dept:
            applicable.append(t)
        elif scope == "employee":
            if emp_id in (t.get("employee_ids") or []):
                applicable.append(t)

    return applicable


# ─── ALLOWANCE ENDPOINTS ──────────────────────────────────────────────────────

@router.get("/payroll-allowances")
async def list_allowances(request: Request):
    await require_auth(request)
    db = get_db()
    docs = await db.da_payroll_allowances.find({}, {"_id": 0}).sort("created_at", 1).to_list(500)
    return {"ok": True, "allowances": [serialize_doc(d) for d in docs]}


@router.post("/payroll-allowances")
async def create_allowance(request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()

    name = (body.get("name") or "").strip()
    if not name: raise HTTPException(400, "name wajib diisi.")

    doc = {
        "allowance_id": _uid(),
        "name": name,
        "amount": float(body.get("amount") or 0),
        "calc_type": body.get("calc_type") or "fixed",   # fixed | percentage_gross
        "applicable_to": body.get("applicable_to") or "all",  # all | department | employee
        "department": body.get("department") or "",
        "employee_ids": body.get("employee_ids") or [],
        "description": body.get("description") or "",
        "is_active": True,
        "created_by": user["id"],
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db.da_payroll_allowances.insert_one(doc)
    return {"ok": True, "allowance": serialize_doc(doc)}


@router.put("/payroll-allowances/{allowance_id}")
async def update_allowance(allowance_id: str, request: Request):
    await require_auth(request)
    db = get_db()
    body = await request.json()
    allowed_keys = ["name", "amount", "calc_type", "applicable_to", "department",
                    "employee_ids", "description", "is_active"]
    upd = {k: body[k] for k in allowed_keys if k in body}
    upd["updated_at"] = _now()
    res = await db.da_payroll_allowances.update_one({"allowance_id": allowance_id}, {"$set": upd})
    if res.matched_count == 0: raise HTTPException(404, "Tunjangan tidak ditemukan.")
    doc = await db.da_payroll_allowances.find_one({"allowance_id": allowance_id}, {"_id": 0})
    return {"ok": True, "allowance": serialize_doc(doc)}


@router.delete("/payroll-allowances/{allowance_id}")
async def delete_allowance(allowance_id: str, request: Request):
    await require_auth(request)
    db = get_db()
    await db.da_payroll_allowances.delete_one({"allowance_id": allowance_id})
    return {"ok": True}


def _uid(): return str(uuid.uuid4())
def _now(): return datetime.now(timezone.utc)


async def _require_hr(request: Request):
    user = await require_auth(request)
    role = (user.get("role") or "").lower()
    if role in ("superadmin", "admin", "owner", "hr", "manager"):
        return user
    perms = user.get("_permissions") or []
    if "*" in perms or "hr.manage" in perms or "payroll.manage" in perms:
        return user
    raise HTTPException(403, "Forbidden: butuh permission HR/payroll.")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ FASE 8b — PAYROLL PROFILES                                                ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@router.get("/payroll-profiles")
async def list_profiles(request: Request, employee_id: Optional[str] = None, active_only: bool = True):
    await require_auth(request)
    db = get_db()
    q = {}
    if active_only:
        q["active"] = True
    if employee_id:
        q["employee_id"] = employee_id
    rows = await db.rahaza_payroll_profiles.find(q, {"_id": 0}).to_list(500)
    # Enrich with employee info
    emp_ids = list({r.get("employee_id") for r in rows if r.get("employee_id")})
    emps = await db.rahaza_employees.find({"id": {"$in": emp_ids}}, {"_id": 0}).to_list(500) if emp_ids else []
    e_map = {e["id"]: e for e in emps}
    for r in rows:
        e = e_map.get(r.get("employee_id")) or {}
        r["employee_code"] = e.get("employee_code")
        r["employee_name"] = e.get("name")
    rows.sort(key=lambda r: r.get("employee_code") or "")
    return serialize_doc(rows)


@router.get("/payroll-profiles/{employee_id}")
async def get_profile(employee_id: str, request: Request):
    await require_auth(request)
    db = get_db()
    row = await db.rahaza_payroll_profiles.find_one({"employee_id": employee_id, "active": True}, {"_id": 0})
    if not row:
        raise HTTPException(404, "Profile payroll belum dibuat untuk pegawai ini.")
    emp = await db.rahaza_employees.find_one({"id": employee_id}, {"_id": 0}) or {}
    row["employee_code"] = emp.get("employee_code")
    row["employee_name"] = emp.get("name")
    return serialize_doc(row)


def _normalize_profile(body: dict) -> dict:
    pay_scheme = (body.get("pay_scheme") or "monthly").lower()
    period_type = (body.get("period_type") or "monthly").lower()
    if pay_scheme not in VALID_SCHEMES:
        raise HTTPException(400, f"pay_scheme harus salah satu: {VALID_SCHEMES}")
    if period_type not in VALID_PERIOD_TYPES:
        raise HTTPException(400, f"period_type harus salah satu: {VALID_PERIOD_TYPES}")
    cutoff = body.get("cutoff_config") or {}
    # Defaults
    if period_type == "weekly" and "week_start_day" not in cutoff:
        cutoff["week_start_day"] = 1  # Monday
    if period_type == "monthly" and "start_day" not in cutoff:
        cutoff["start_day"] = 1  # 1st of month
    # Validate ranges
    wsd = cutoff.get("week_start_day")
    if wsd is not None and (not isinstance(wsd, int) or not (0 <= wsd <= 6)):
        raise HTTPException(400, "week_start_day harus 0..6 (0=Senin..6=Minggu)")
    sd = cutoff.get("start_day")
    if sd is not None and (not isinstance(sd, int) or not (1 <= sd <= 28)):
        raise HTTPException(400, "start_day harus 1..28")
    pcs_rates = body.get("pcs_process_rates") or []
    norm_pcs_rates = []
    for r in pcs_rates:
        if not r.get("process_id"):
            continue
        norm_pcs_rates.append({
            "process_id": r["process_id"],
            "process_code": (r.get("process_code") or "").upper(),
            "rate": float(r.get("rate") or 0),
        })
    return {
        "employee_id": body.get("employee_id"),
        "pay_scheme": pay_scheme,
        "period_type": period_type,
        "cutoff_config": cutoff,
        "base_rate": float(body.get("base_rate") or 0),
        "overtime_rate": float(body.get("overtime_rate") or 0),
        "pcs_process_rates": norm_pcs_rates,
        "notes": body.get("notes") or "",
    }


@router.post("/payroll-profiles")
async def upsert_profile(request: Request):
    user = await _require_hr(request)
    db = get_db()
    body = await request.json()
    emp_id = body.get("employee_id")
    if not emp_id:
        raise HTTPException(400, "employee_id wajib.")
    emp = await db.rahaza_employees.find_one({"id": emp_id}, {"_id": 0})
    if not emp:
        raise HTTPException(404, f"Pegawai dengan id={emp_id} tidak ditemukan.")
    doc = _normalize_profile(body)
    existing = await db.rahaza_payroll_profiles.find_one({"employee_id": emp_id, "active": True}, {"_id": 0})
    now = _now()
    doc.update({
        "active": True,
        "updated_at": now,
        "updated_by": user["id"],
        "updated_by_name": user.get("name", ""),
    })
    if existing:
        await db.rahaza_payroll_profiles.update_one({"id": existing["id"]}, {"$set": doc})
        out = await db.rahaza_payroll_profiles.find_one({"id": existing["id"]}, {"_id": 0})
    else:
        doc["id"] = _uid()
        doc["created_at"] = now
        doc["created_by"] = user["id"]
        doc["created_by_name"] = user.get("name", "")
        await db.rahaza_payroll_profiles.insert_one(doc)
        out = await db.rahaza_payroll_profiles.find_one({"id": doc["id"]}, {"_id": 0})
    await log_activity(user["id"], user.get("name", ""), "upsert", "rahaza.payroll_profile", emp_id)
    out["employee_code"] = emp.get("employee_code")
    out["employee_name"] = emp.get("name")
    return serialize_doc(out)


@router.put("/payroll-profiles/{pid}")
async def update_profile(pid: str, request: Request):
    user = await _require_hr(request)
    db = get_db()
    existing = await db.rahaza_payroll_profiles.find_one({"id": pid}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Profile tidak ditemukan.")
    body = await request.json()
    body["employee_id"] = existing["employee_id"]  # cannot change
    doc = _normalize_profile(body)
    doc.update({
        "updated_at": _now(),
        "updated_by": user["id"],
        "updated_by_name": user.get("name", ""),
    })
    await db.rahaza_payroll_profiles.update_one({"id": pid}, {"$set": doc})
    out = await db.rahaza_payroll_profiles.find_one({"id": pid}, {"_id": 0})
    return serialize_doc(out)


@router.delete("/payroll-profiles/{pid}")
async def delete_profile(pid: str, request: Request):
    user = await _require_hr(request)
    db = get_db()
    res = await db.rahaza_payroll_profiles.update_one({"id": pid, "active": True}, {"$set": {"active": False, "updated_at": _now(), "updated_by": user["id"]}})
    if res.matched_count == 0:
        raise HTTPException(404, "Profile tidak ditemukan atau sudah nonaktif.")
    return {"status": "deleted"}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ FASE 8c — PAYROLL RUN & PAYSLIP                                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def _to_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _date_range_filter(from_iso: str, to_iso: str) -> dict:
    return {"$gte": from_iso, "$lte": to_iso}


async def _generate_run_number(db) -> str:
    today = date.today().strftime("%Y%m%d")
    prefix = f"PR-{today}-"
    count = await db.rahaza_payroll_runs.count_documents({"run_number": {"$regex": f"^{prefix}"}})
    return f"{prefix}{count+1:03d}"


async def _compute_payslip_for_employee(db, profile: dict, period_from: str, period_to: str, emp: dict) -> dict:
    """Hitung slip payroll untuk 1 pegawai berdasarkan profile + window."""
    scheme = profile["pay_scheme"]
    base_rate = float(profile.get("base_rate") or 0)
    ot_rate = float(profile.get("overtime_rate") or 0)
    emp_id = profile["employee_id"]

    earnings = []
    source_refs = {"wip_event_count": 0, "attendance_event_count": 0, "process_breakdown": {}}

    # Query attendance untuk periode
    att_rows = await db.rahaza_attendance_events.find({
        "employee_id": emp_id,
        "date": _date_range_filter(period_from, period_to),
    }, {"_id": 0}).to_list(500)
    source_refs["attendance_event_count"] = len(att_rows)
    total_hours = sum(float(r.get("hours_worked") or 0) for r in att_rows)
    total_ot = sum(float(r.get("overtime_hours") or 0) for r in att_rows)
    days_hadir = sum(1 for r in att_rows if r.get("status") == "hadir")

    # ─── Include Approved Overtime Requests (P1.1) ────────────────────────────
    # Approved overtime requests are stored in rahaza_overtime_requests with
    # hours + rate_multiplier. We normalize to base-rate-equivalent hours by
    # scaling (rate_multiplier / base_ot_rate_multiplier=1.5) so the fixed
    # ot_rate below still produces the correct pay. Example: 2 hours × 2.0 tier
    # = 2.67 effective hours at 1.5× tier.
    try:
        ot_approved = await db.rahaza_overtime_requests.find({
            "employee_id": emp_id,
            "status": "approved",
            "date": _date_range_filter(period_from, period_to),
        }, {"_id": 0}).to_list(500)
        for ot in ot_approved:
            # weighted by rate_multiplier
            total_ot += float(ot.get("hours") or 0) * float(ot.get("rate_multiplier") or 1.5) / 1.5
            # We keep the base multiplier as 1.5 in ot_rate; effectively we boost hours
        source_refs["overtime_request_count"] = len(ot_approved)
    except Exception as e:
        log.warning(f"Overtime request aggregation failed: {e}")

    if scheme == "pcs":
        # Sum WIP events output oleh operator ini dalam periode
        # Event date bisa dicompare via string ISO karena format ISO cocok lexicographic
        wip_rows = await db.rahaza_wip_events.find({
            "operator_id": emp_id,
            "event_type": "output",
            "event_date": _date_range_filter(period_from, period_to),
        }, {"_id": 0}).to_list(500)
        source_refs["wip_event_count"] = len(wip_rows)
        # Group by process_id
        proc_map = {}
        for ev in wip_rows:
            pid = ev.get("process_id") or "unknown"
            if pid not in proc_map:
                proc_map[pid] = {"qty": 0, "events": 0, "process_code": ev.get("process_code") or ""}
            proc_map[pid]["qty"] += int(ev.get("qty") or 0)
            proc_map[pid]["events"] += 1
            if ev.get("process_code"):
                proc_map[pid]["process_code"] = ev["process_code"]
        # Cari rate per process (override) atau base_rate
        rate_overrides = {r["process_id"]: r["rate"] for r in (profile.get("pcs_process_rates") or [])}
        for pid, info in proc_map.items():
            rate = float(rate_overrides.get(pid, base_rate))
            amount = round(info["qty"] * rate)
            label = f"Borongan pcs · {info.get('process_code') or 'Proses'}"
            earnings.append({
                "label": label,
                "qty": info["qty"],
                "unit": "pcs",
                "rate": rate,
                "amount": amount,
            })
            source_refs["process_breakdown"][info.get("process_code") or pid] = {
                "qty": info["qty"],
                "rate": rate,
                "amount": amount,
            }
    elif scheme == "hourly":
        amount = round(total_hours * base_rate)
        earnings.append({
            "label": "Borongan jam",
            "qty": round(total_hours, 2),
            "unit": "jam",
            "rate": base_rate,
            "amount": amount,
        })
    elif scheme == "weekly":
        try:
            d_from = _to_date(period_from)
            d_to = _to_date(period_to)
            days = (d_to - d_from).days + 1
            weeks = max(1, round(days / 7))
        except Exception:
            weeks = 1
        amount = round(weeks * base_rate)
        earnings.append({
            "label": "Gaji mingguan",
            "qty": weeks,
            "unit": "minggu",
            "rate": base_rate,
            "amount": amount,
        })
    elif scheme == "monthly":
        amount = round(base_rate)
        earnings.append({
            "label": "Gaji bulanan",
            "qty": 1,
            "unit": "bulan",
            "rate": base_rate,
            "amount": amount,
        })

    earnings_total = sum(e["amount"] for e in earnings)
    overtime_amount = round(total_ot * ot_rate)
    gross = earnings_total + overtime_amount

    # ─── Tambahkan Tunjangan Tetap (DA Allowances) ────────────────────────────
    allowances = await _get_applicable_allowances(db, emp)
    allowance_items = []
    for alw in allowances:
        if alw.get("calc_type") == "percentage_gross":
            amount = round(gross * float(alw.get("amount") or 0) / 100)
        else:
            amount = round(float(alw.get("amount") or 0))
        if amount > 0:
            allowance_items.append({
                "label": alw.get("name", "Tunjangan"),
                "allowance_id": alw.get("allowance_id"),
                "amount": amount,
                "calc_type": alw.get("calc_type", "fixed"),
            })
    allowance_total = sum(a["amount"] for a in allowance_items)
    gross += allowance_total

    # ─── PPh21 + BPJS Auto-Deduction (P0.4 + P0.5) ────────────────────────────
    deductions = []
    deductions_total = 0

    # ─── LWOP (Leave Without Pay) Potongan ────────────────────────────────────
    try:
        # Fetch leave types yang unpaid (LWOP)
        lwop_type_ids = set()
        async for lt in db.rahaza_leave_types.find({"unpaid": True, "active": True}, {"_id": 0, "id": 1}):
            lwop_type_ids.add(lt["id"])

        if lwop_type_ids and scheme == "monthly" and base_rate > 0:
            # Fetch approved LWOP leaves dalam payroll period
            lwop_leaves = await db.rahaza_leave_requests.find({
                "employee_id":  emp_id,
                "status":       "approved",
                "leave_type_id": {"$in": list(lwop_type_ids)},
                "from_date":    {"$lte": period_to},
                "to_date":      {"$gte": period_from},
            }, {"_id": 0}).to_list(100)

            if lwop_leaves:
                # Hitung total hari LWOP dalam period (pakai duration_working_days jika ada)
                lwop_days = sum(
                    float(lv.get("duration_working_days") or lv.get("duration_days") or 0)
                    for lv in lwop_leaves
                )

                if lwop_days > 0:
                    # Hitung working days dalam periode dari production calendar
                    try:
                        pf = date.fromisoformat(period_from[:10])
                        pt = date.fromisoformat(period_to[:10])
                        hol_docs = await db.rahaza_production_calendar.find(
                            {"date": {"$gte": period_from[:10], "$lte": period_to[:10]}, "type": "holiday"},
                            {"_id": 0, "date": 1}
                        ).to_list(50)
                        holiday_set = {h["date"] for h in hol_docs}
                        working_days_in_period = 0
                        cur = pf
                        while cur <= pt:
                            if cur.weekday() < 5 and cur.isoformat() not in holiday_set:
                                working_days_in_period += 1
                            cur += timedelta(days=1)
                        if working_days_in_period == 0:
                            working_days_in_period = 22  # fallback
                    except Exception:
                        working_days_in_period = 22

                    daily_rate   = round(base_rate / working_days_in_period)
                    lwop_amount  = round(daily_rate * lwop_days)

                    deductions.append({
                        "label":       f"Potongan LWOP / Cuti Tanpa Gaji ({lwop_days:.1f} hari)",
                        "type":        "lwop",
                        "days":        lwop_days,
                        "daily_rate":  daily_rate,
                        "amount":      lwop_amount,
                    })
                    deductions_total += lwop_amount
                    source_refs["lwop_days"]   = lwop_days
                    source_refs["lwop_amount"] = lwop_amount
    except Exception as e:
        log.warning(f"LWOP deduction calculation failed for {emp_id}: {e}")
    try:
        from routes.rahaza_payroll_tax import compute_full_tax_and_bpjs
        apply_bpjs   = bool(emp.get("bpjs_kesehatan_number") or emp.get("bpjs_ketenagakerjaan_number"))
        apply_pph21  = bool(emp.get("npwp_number") or emp.get("tax_ptkp"))
        if scheme in ("monthly", "bulanan") and (apply_bpjs or apply_pph21):
            # PPh21 dihitung dari gross SETELAH LWOP dipotong
            gross_after_lwop = gross - (source_refs.get("lwop_amount") or 0)
            tax_calc = compute_full_tax_and_bpjs(
                monthly_gross=max(0, gross_after_lwop),
                ptkp_code=emp.get("tax_ptkp") or "TK/0",
                apply_bpjs=apply_bpjs,
                apply_pph21=apply_pph21,
                include_ketenagakerjaan=bool(emp.get("bpjs_ketenagakerjaan_number")),
                jkk_risk_tier="very_low",
            )
            # Merge: LWOP deductions sudah di list + tambah tax deductions
            deductions = deductions + tax_calc["deductions"]
            deductions_total += tax_calc["total_deductions"]
    except Exception as e:
        log.warning(f"PPh21/BPJS calculation failed for {emp_id}: {e}")

    net_pay = gross - deductions_total

    payslip = {
        "id": _uid(),
        "employee_id": emp_id,
        "employee_code": emp.get("employee_code"),
        "employee_name": emp.get("name"),
        "department": emp.get("department") or "",
        "pay_scheme": scheme,
        "period_from": period_from,
        "period_to": period_to,
        "earnings": earnings,
        "earnings_total": earnings_total,
        "overtime_hours": round(total_ot, 2),
        "overtime_rate": ot_rate,
        "overtime_amount": overtime_amount,
        "allowances": allowance_items,
        "allowance_total": allowance_total,
        "total_hours_worked": round(total_hours, 2),
        "days_hadir": days_hadir,
        "gross_pay": gross,
        "deductions": deductions,
        "deductions_total": deductions_total,
        "net_pay": net_pay,
        "source_refs": source_refs,
        "notes": "",
    }
    return payslip


@router.get("/payroll-runs")
async def list_runs(request: Request, status: Optional[str] = None, limit: int = 50, skip: int = 0):
    await require_auth(request)
    db = get_db()
    q = {}
    if status:
        q["status"] = status
    rows = await db.rahaza_payroll_runs.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(500)
    return serialize_doc(rows)


@router.post("/payroll-runs")
async def create_run(request: Request):
    user = await _require_hr(request)
    db = get_db()
    body = await request.json()
    period_from = (body.get("period_from") or "").strip()
    period_to = (body.get("period_to") or "").strip()
    if not (period_from and period_to):
        raise HTTPException(400, "period_from & period_to wajib (YYYY-MM-DD).")
    try:
        _to_date(period_from); _to_date(period_to)
    except Exception:
        raise HTTPException(400, "Format tanggal harus YYYY-MM-DD.")
    if period_from > period_to:
        raise HTTPException(400, "period_from tidak boleh > period_to.")

    # Ambil profile aktif
    employee_ids = body.get("employee_ids") or []
    q = {"active": True}
    if employee_ids:
        q["employee_id"] = {"$in": employee_ids}
    profiles = await db.rahaza_payroll_profiles.find(q, {"_id": 0}).to_list(500)
    if not profiles:
        raise HTTPException(400, "Tidak ada payroll profile aktif untuk diproses. Buat profile dulu di menu Payroll Profiles.")

    emp_ids = [p["employee_id"] for p in profiles]
    emps = await db.rahaza_employees.find({"id": {"$in": emp_ids}}, {"_id": 0}).to_list(500)
    e_map = {e["id"]: e for e in emps}

    # Create run header
    run_number = await _generate_run_number(db)
    run_id = _uid()
    now = _now()

    # Generate payslips
    payslips = []
    for p in profiles:
        emp = e_map.get(p["employee_id"])
        if not emp:
            continue
        slip = await _compute_payslip_for_employee(db, p, period_from, period_to, emp)
        slip.update({
            "run_id": run_id,
            "run_number": run_number,
            "created_at": now,
            "updated_at": now,
        })
        payslips.append(slip)

    # ── Saga pattern: atomic payslip insert + run header insert ─────────────────
    # Since MongoDB standalone doesn't support multi-document transactions,
    # we use a compensation saga: if run header insert fails, payslips are deleted.
    payslips_inserted = False

    total_gross = sum(s["gross_pay"] for s in payslips)
    total_ded = sum(s["deductions_total"] for s in payslips)
    total_net = sum(s["net_pay"] for s in payslips)

    run_doc = {
        "id": run_id,
        "run_number": run_number,
        "period_from": period_from,
        "period_to": period_to,
        "status": "draft",
        "total_employees": len(payslips),
        "total_gross": total_gross,
        "total_deductions": total_ded,
        "total_net": total_net,
        "notes": body.get("notes") or "",
        "created_at": now,
        "created_by": user["id"],
        "created_by_name": user.get("name", ""),
        "updated_at": now,
    }

    async def _insert_payslips():
        nonlocal payslips_inserted
        if payslips:
            await db.rahaza_payslips.insert_many(payslips)
        payslips_inserted = True

    async def _compensate_payslips():
        await db.rahaza_payslips.delete_many({"run_id": run_id})

    async def _insert_run_header():
        await db.rahaza_payroll_runs.insert_one(run_doc)

    saga = SagaExecutor(name="create_payroll_run")
    saga.add_step(
        name="insert_payslips",
        action=_insert_payslips,
        compensate=_compensate_payslips,
    )
    saga.add_step(
        name="insert_run_header",
        action=_insert_run_header,
        compensate=lambda: db.rahaza_payroll_runs.delete_one({"id": run_id}),
    )
    saga_result = await saga.execute()
    if not saga_result.success:
        log.error(f"Saga failed creating payroll run {run_number}: {saga_result.error_detail}")
        raise HTTPException(500, f"Gagal membuat payroll run: {saga_result.error_detail}")

    await log_activity(user["id"], user.get("name", ""), "create", "rahaza.payroll_run", run_number)
    out = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    return serialize_doc(out)


@router.get("/payroll-runs/{run_id}")
async def get_run(run_id: str, request: Request):
    await require_auth(request)
    db = get_db()
    run = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Payroll run tidak ditemukan.")
    payslips = await db.rahaza_payslips.find({"run_id": run_id}, {"_id": 0}).sort("employee_code", 1).to_list(500)
    return serialize_doc({"run": run, "payslips": payslips})


@router.post("/payroll-runs/{run_id}/finalize")
async def finalize_run(run_id: str, request: Request):
    user = await _require_hr(request)
    db = get_db()
    run = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Payroll run tidak ditemukan.")
    if run.get("status") != "draft":
        raise HTTPException(400, f"Run sudah ber-status '{run.get('status')}', tidak bisa finalize.")
    # Recalc totals dari payslips (in case deductions diubah)
    payslips = await db.rahaza_payslips.find({"run_id": run_id}, {"_id": 0}).to_list(500)
    total_gross = sum(s.get("gross_pay", 0) for s in payslips)
    total_ded = sum(s.get("deductions_total", 0) for s in payslips)
    total_net = sum(s.get("net_pay", 0) for s in payslips)
    await db.rahaza_payroll_runs.update_one({"id": run_id}, {"$set": {
        "status": "finalized",
        "total_gross": total_gross,
        "total_deductions": total_ded,
        "total_net": total_net,
        "finalized_at": _now(),
        "finalized_by": user["id"],
        "finalized_by_name": user.get("name", ""),
        "updated_at": _now(),
    }})
    await log_activity(user["id"], user.get("name", ""), "finalize", "rahaza.payroll_run", run.get("run_number"))
    out = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})

    # ── F3 Auto-post Payroll JE
    posting_result = None
    try:
        posting_result = await post_payroll_run(db, out, user)
    except Exception as e:
        log.exception("Payroll auto-post failed")
        posting_result = {"ok": False, "error": str(e)}
    out = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})

    # ── Notifikasi payslip siap ke semua karyawan dalam run ini ──────────────
    try:
        from routes.rahaza_notifications import publish_notification
        # Kumpulkan user_id dari employees dalam run
        payslip_emps = await db.rahaza_payslips.find(
            {"run_id": run_id}, {"_id": 0, "employee_id": 1, "net_pay": 1}
        ).to_list(500)
        emp_ids_in_run = [s["employee_id"] for s in payslip_emps]
        if emp_ids_in_run:
            linked_emps = await db.rahaza_employees.find(
                {"id": {"$in": emp_ids_in_run}, "user_id": {"$exists": True, "$ne": None}},
                {"_id": 0, "user_id": 1, "name": 1}
            ).to_list(500)
            for le in linked_emps:
                net = next((s["net_pay"] for s in payslip_emps if s["employee_id"] == le.get("id")), 0)
                await publish_notification(
                    db,
                    type_="payslip_ready",
                    severity="info",
                    title="Slip Gaji Tersedia",
                    message=(
                        f"Slip gaji periode {out.get('period_from','')[:7]} sudah tersedia. "
                        f"Take-home: Rp {net:,.0f}."
                    ),
                    link_module="self-dashboard",
                    target_user_ids=[le["user_id"]],
                    dedup_key=f"payslip_ready_{run_id}_{le['user_id']}",
                )
    except Exception as ne:
        log.warning(f"[payroll] payslip notif failed: {ne}")

    out["_posting_result"] = posting_result
    return serialize_doc(out)


@router.post("/payroll-runs/{run_id}/post-to-gl")
async def retry_post_payroll(run_id: str, request: Request):
    """F3: manual retry post payroll run to GL (idempotent)."""
    user = await _require_hr(request)
    db = get_db()
    run = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Payroll run tidak ditemukan.")
    if run.get("status") != "finalized":
        raise HTTPException(400, "Hanya run yang sudah finalized yang bisa di-post.")
    result = await post_payroll_run(db, run, user)
    out = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    out["_posting_result"] = result
    return serialize_doc(out)


@router.post("/payroll-runs/{run_id}/retry-post")
async def retry_post_alias(run_id: str, request: Request):
    """Alias untuk /post-to-gl (backward compat frontend)."""
    return await retry_post_payroll(run_id, request)


@router.post("/payroll-runs/{run_id}/pay")
async def pay_payroll_run(run_id: str, request: Request):
    """
    Tandai gaji sebagai sudah dibayar dan buat Payment JE.
    Dr 2-1200 Hutang Gaji / Cr [bank_account_code].
    Body: { payment_date, bank_account_code, payment_method, notes }
    """
    user = await _require_hr(request)
    db   = get_db()
    body = await request.json()

    run = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Payroll run tidak ditemukan.")
    if run.get("status") != "finalized":
        raise HTTPException(400, "Hanya run FINALIZED yang bisa dibayar.")
    if run.get("payment_status") == "paid":
        raise HTTPException(400,
            f"Penggajian {run.get('run_number')} sudah dibayar "
            f"({run.get('payment_gl_je_number')}). "
            "Gunakan void-payment untuk membatalkan.")

    payment_date   = (body.get("payment_date") or str(date.today()))[:10]
    bank_code      = (body.get("bank_account_code") or "1-1201").strip()
    payment_method = body.get("payment_method") or "bank_transfer"
    notes          = (body.get("notes") or "").strip()

    # Validate bank CoA exists
    bank_acc = await db.rahaza_coa_accounts.find_one(
        {"code": bank_code, "active": True}, {"_id": 0, "name": 1}
    )
    if not bank_acc:
        raise HTTPException(400, f"Akun GL '{bank_code}' tidak ditemukan atau tidak aktif.")

    from routes.rahaza_posting import post_payroll_payment
    result = await post_payroll_payment(db, run, payment_date, bank_code, user)

    update = {
        "payment_status":       "paid" if result.get("ok") else "payment_error",
        "payment_method":       payment_method,
        "payment_date":         payment_date,
        "payment_bank_code":    bank_code,
        "payment_bank_name":    bank_acc.get("name", ""),
        "payment_notes":        notes,
        "payment_gl_je_id":     result.get("je_id"),
        "payment_gl_je_number": result.get("je_number"),
        "payment_error":        result.get("error"),
        "paid_at":              _now(),
        "paid_by":              user["id"],
        "paid_by_name":         user.get("name", ""),
        "updated_at":           _now(),
    }
    await db.rahaza_payroll_runs.update_one({"id": run_id}, {"$set": update})
    await log_activity(user["id"], user.get("name", ""), "pay_payroll", "rahaza.payroll_run",
                       f"{run.get('run_number')} → {bank_code} {payment_date}")
    out = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    out["_payment_result"] = result
    return serialize_doc(out)


@router.post("/payroll-runs/{run_id}/void-payment")
async def void_payroll_payment_endpoint(run_id: str, request: Request):
    """
    Batalkan jurnal pembayaran gaji (void payment JE).
    Hanya bisa dilakukan jika payment JE masih aktif.
    Body: { reason }
    """
    user = await _require_hr(request)
    db   = get_db()
    body = await request.json()
    reason = body.get("reason") or "Pembatalan pembayaran gaji"

    run = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Payroll run tidak ditemukan.")
    if run.get("payment_status") != "paid":
        raise HTTPException(400, "Tidak ada pembayaran aktif yang bisa dibatalkan.")

    from routes.rahaza_posting import void_payroll_payment
    result = await void_payroll_payment(db, run_id, user, reason)
    await db.rahaza_payroll_runs.update_one(
        {"id": run_id},
        {"$set": {"payment_status": "void", "updated_at": _now()}}
    )
    await log_activity(user["id"], user.get("name", ""), "void_payment", "rahaza.payroll_run",
                       f"{run.get('run_number')} — {reason}")
    out = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    return serialize_doc(out)


@router.delete("/payroll-runs/{run_id}")
async def delete_run(run_id: str, request: Request):
    await _require_hr(request)
    db = get_db()
    run = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Payroll run tidak ditemukan.")
    if run.get("status") == "finalized":
        raise HTTPException(400, "Run yang sudah finalized tidak bisa dihapus. Gunakan cancel atau buat run baru.")
    await db.rahaza_payslips.delete_many({"run_id": run_id})
    await db.rahaza_payroll_runs.delete_one({"id": run_id})
    return {"status": "deleted"}


@router.post("/payroll-runs/{run_id}/pay-bpjs")
async def pay_bpjs(run_id: str, request: Request):
    """
    Bayar BPJS dari payroll run ini.
    Dr 2-1500 Hutang BPJS / Cr [bank_code].
    Body: { payment_date, bank_account_code, notes }
    """
    user = await _require_hr(request)
    db   = get_db()
    body = await request.json()
    run  = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    if not run: raise HTTPException(404, "Run tidak ditemukan.")
    if run.get("status") != "finalized": raise HTTPException(400, "Hanya run FINALIZED.")
    if run.get("bpjs_payment_status") == "paid":
        raise HTTPException(400, "BPJS run ini sudah dibayar.")

    payment_date = (body.get("payment_date") or str(date.today()))[:10]
    bank_code    = (body.get("bank_account_code") or "1-1201").strip()
    notes        = body.get("notes") or ""

    # Calculate BPJS total from payslips
    slips  = await db.rahaza_payslips.find({"run_id": run_id}, {"_id": 0, "deductions": 1}).to_list(500)
    bpjs_total = 0.0
    for s in slips:
        for d in (s.get("deductions") or []):
            if "bpjs" in (d.get("label") or "").lower() or d.get("type") == "bpjs":
                bpjs_total += float(d.get("amount") or 0)

    if bpjs_total <= 0:
        raise HTTPException(400, "Tidak ada potongan BPJS di run ini.")

    # Build JE: Dr Hutang BPJS / Cr Bank
    bank_acc = await db.rahaza_coa_accounts.find_one({"code": bank_code, "active": True}, {"_id": 0, "name": 1})
    if not bank_acc: raise HTTPException(400, f"Akun GL '{bank_code}' tidak ditemukan.")

    from routes.rahaza_posting import _create_posted_je, _now as _p_now
    run_id_ref = f"bpjspay:{run_id}"
    try:
        je_date = date.fromisoformat(payment_date)
    except Exception:
        je_date = date.today()
    memo  = f"Bayar BPJS {run.get('run_number')} · {run.get('period_from')}–{run.get('period_to')}"
    lines = [
        {"account_code": "2-1500", "debit": bpjs_total, "credit": 0, "description": memo},
        {"account_code": bank_code, "debit": 0, "credit": bpjs_total, "description": memo},
    ]
    result = await _create_posted_je(db, je_date, memo, "bpjs_payment", run_id_ref, lines, user)
    update = {
        "bpjs_payment_status":  "paid" if result.get("ok") else "error",
        "bpjs_payment_date":    payment_date,
        "bpjs_payment_amount":  bpjs_total,
        "bpjs_payment_je":      result.get("je_number"),
        "bpjs_payment_error":   result.get("error"),
        "updated_at":           _now(),
    }
    await db.rahaza_payroll_runs.update_one({"id": run_id}, {"$set": update})
    await log_activity(user["id"], user.get("name",""), "pay_bpjs", "rahaza.payroll_run",
                       f"{run.get('run_number')} BPJS Rp {bpjs_total:,.0f}")
    out = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    out["_payment_result"] = result
    return serialize_doc(out)


@router.post("/payroll-runs/{run_id}/pay-pph21")
async def pay_pph21(run_id: str, request: Request):
    """
    Bayar PPh21 dari payroll run ini ke DJP.
    Dr 2-1301 Hutang PPh21 / Cr [bank_code].
    Body: { payment_date, bank_account_code, notes }
    """
    user = await _require_hr(request)
    db   = get_db()
    body = await request.json()
    run  = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    if not run: raise HTTPException(404, "Run tidak ditemukan.")
    if run.get("status") != "finalized": raise HTTPException(400, "Hanya run FINALIZED.")
    if run.get("pph21_payment_status") == "paid":
        raise HTTPException(400, "PPh21 run ini sudah dibayar.")

    payment_date = (body.get("payment_date") or str(date.today()))[:10]
    bank_code    = (body.get("bank_account_code") or "1-1201").strip()

    slips = await db.rahaza_payslips.find({"run_id": run_id}, {"_id": 0, "deductions": 1}).to_list(500)
    pph_total = 0.0
    for s in slips:
        for d in (s.get("deductions") or []):
            if "pph" in (d.get("label") or "").lower() or d.get("type") == "pph21":
                pph_total += float(d.get("amount") or 0)

    if pph_total <= 0: raise HTTPException(400, "Tidak ada potongan PPh21 di run ini.")

    bank_acc = await db.rahaza_coa_accounts.find_one({"code": bank_code, "active": True}, {"_id": 0, "name": 1})
    if not bank_acc: raise HTTPException(400, f"Akun GL '{bank_code}' tidak ditemukan.")

    from routes.rahaza_posting import _create_posted_je
    run_id_ref = f"pph21pay:{run_id}"
    try:
        je_date = date.fromisoformat(payment_date)
    except Exception:
        je_date = date.today()
    memo  = f"Bayar PPh21 {run.get('run_number')} · {run.get('period_from')}–{run.get('period_to')}"
    lines = [
        {"account_code": "2-1301", "debit": pph_total, "credit": 0, "description": memo},
        {"account_code": bank_code, "debit": 0, "credit": pph_total, "description": memo},
    ]
    result = await _create_posted_je(db, je_date, memo, "pph21_payment", run_id_ref, lines, user)
    update = {
        "pph21_payment_status": "paid" if result.get("ok") else "error",
        "pph21_payment_date":   payment_date,
        "pph21_payment_amount": pph_total,
        "pph21_payment_je":     result.get("je_number"),
        "pph21_payment_error":  result.get("error"),
        "updated_at":           _now(),
    }
    await db.rahaza_payroll_runs.update_one({"id": run_id}, {"$set": update})
    await log_activity(user["id"], user.get("name",""), "pay_pph21", "rahaza.payroll_run",
                       f"{run.get('run_number')} PPh21 Rp {pph_total:,.0f}")
    out = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    out["_payment_result"] = result
    return serialize_doc(out)


@router.get("/payroll-runs/{run_id}/export")
async def export_run_csv(run_id: str, request: Request):
    await require_auth(request)
    db = get_db()
    run = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Payroll run tidak ditemukan.")
    payslips = await db.rahaza_payslips.find({"run_id": run_id}, {"_id": 0}).sort("employee_code", 1).to_list(500)

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "run_number", "period_from", "period_to",
        "employee_code", "employee_name", "pay_scheme",
        "earnings_total", "overtime_hours", "overtime_amount",
        "gross_pay", "deductions_total", "net_pay",
        "days_hadir", "total_hours_worked",
    ])
    for s in payslips:
        w.writerow([
            run.get("run_number"), run.get("period_from"), run.get("period_to"),
            s.get("employee_code"), s.get("employee_name"), s.get("pay_scheme"),
            s.get("earnings_total", 0), s.get("overtime_hours", 0), s.get("overtime_amount", 0),
            s.get("gross_pay", 0), s.get("deductions_total", 0), s.get("net_pay", 0),
            s.get("days_hadir", 0), s.get("total_hours_worked", 0),
        ])
    buf.seek(0)
    filename = f"payroll_{run.get('run_number')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── PDF helpers ────────────────────────────────────────────────────────────────

def _idr(n):
    """Format angka ke Rupiah Indonesia, contoh: 1500000 → Rp 1.500.000"""
    try:
        n = int(round(float(n or 0)))
    except Exception:
        n = 0
    return f"Rp {n:,}".replace(",", ".")


def _build_payslip_pdf(slip: dict, run: dict) -> io.BytesIO:
    """
    Generate satu halaman slip gaji (A5) untuk satu karyawan.
    Mengembalikan BytesIO berisi PDF.
    """
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A5,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    W = A5[0] - 24 * mm  # usable width

    # ── styles ────────────────────────────────────────────────────────────────
    getSampleStyleSheet()
    NAVY   = colors.HexColor("#1a2a4a")
    TEAL   = colors.HexColor("#0f6b8e")
    LIGHT  = colors.HexColor("#f0f6fa")
    GREY   = colors.HexColor("#6b7280")
    BLACK  = colors.black
    WHITE  = colors.white
    GREEN  = colors.HexColor("#1a7a4a")
    RED    = colors.HexColor("#b91c1c")

    h1  = ParagraphStyle("h1",  fontSize=13, fontName="Helvetica-Bold",  textColor=NAVY,  leading=16)
    ParagraphStyle("h2",  fontSize=9,  fontName="Helvetica",       textColor=TEAL,  leading=12)
    h3  = ParagraphStyle("h3",  fontSize=7,  fontName="Helvetica",       textColor=GREY,  leading=9)
    lbl = ParagraphStyle("lbl", fontSize=7.5, fontName="Helvetica-Bold", textColor=NAVY,  leading=10)
    val = ParagraphStyle("val", fontSize=7.5, fontName="Helvetica",      textColor=BLACK, leading=10)
    mono= ParagraphStyle("mono",fontSize=7.5, fontName="Courier",        textColor=BLACK, leading=10)
    ParagraphStyle("rgt", fontSize=7.5, fontName="Helvetica",      textColor=BLACK, leading=10, alignment=TA_RIGHT)
    net_style = ParagraphStyle("net", fontSize=11, fontName="Helvetica-Bold", textColor=WHITE, alignment=TA_RIGHT, leading=14)
    net_lbl   = ParagraphStyle("netl",fontSize=9,  fontName="Helvetica-Bold", textColor=WHITE, leading=12)

    # ── header: company logo + slip info ─────────────────────────────────────
    # Get company config (optional)
    company_tbl = Table(
        [[
            Paragraph("<b>CV. DEWI ADITYA</b>", h1),
            Paragraph(f"<b>SLIP GAJI</b><br/><font size='7' color='#6b7280'>{run.get('run_number', '')}</font>", ParagraphStyle("sr", fontSize=9, fontName="Helvetica-Bold", textColor=TEAL, alignment=TA_RIGHT, leading=12)),
        ]],
        colWidths=[W * 0.6, W * 0.4],
    )
    company_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    sub_tbl = Table(
        [[
            Paragraph("Industri Garmen · CV. Dewi Aditya", h3),
            Paragraph(
                f"Periode: {slip.get('period_from', '')} s/d {slip.get('period_to', '')}",
                ParagraphStyle("pd", fontSize=7, fontName="Helvetica", textColor=GREY, alignment=TA_RIGHT, leading=9)
            ),
        ]],
        colWidths=[W * 0.6, W * 0.4],
    )
    sub_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # ── employee info box ──────────────────────────────────────────────────────
    scheme_labels = {"pcs": "Borongan Pcs", "hourly": "Borongan Jam", "weekly": "Mingguan", "monthly": "Bulanan"}
    scheme = scheme_labels.get(slip.get("pay_scheme", ""), slip.get("pay_scheme", "-"))
    emp_rows = [
        ["Nama Karyawan", slip.get("employee_name", "-"), "Kode", slip.get("employee_code", "-")],
        ["Skema Gaji",    scheme,                          "Hadir", f"{slip.get('days_hadir', 0)} hari"],
        ["Jam Kerja",     f"{slip.get('total_hours_worked', 0)} jam", "Lembur", f"{slip.get('overtime_hours', 0)} jam"],
    ]
    emp_tbl = Table(
        [
            [Paragraph(r[0], lbl), Paragraph(str(r[1]), val), Paragraph(r[2], lbl), Paragraph(str(r[3]), val)]
            for r in emp_rows
        ],
        colWidths=[W * 0.22, W * 0.33, W * 0.16, W * 0.29],
    )
    emp_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), LIGHT),
        ("ROWBACKGROUND",(0, 0), (-1, 0),  colors.HexColor("#dbeaf4")),
        ("BOX",          (0, 0), (-1, -1), 0.5, TEAL),
        ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#c0d8e8")),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))

    # ── earnings table ──────────────────────────────────────────────────────────
    earn_header = [
        Paragraph("Uraian Pendapatan", lbl),
        Paragraph("Qty", ParagraphStyle("lbl_c", fontSize=7.5, fontName="Helvetica-Bold", textColor=NAVY, alignment=TA_RIGHT, leading=10)),
        Paragraph("Satuan", ParagraphStyle("lbl_c2", fontSize=7.5, fontName="Helvetica-Bold", textColor=NAVY, alignment=TA_RIGHT, leading=10)),
        Paragraph("Jumlah", ParagraphStyle("lbl_r", fontSize=7.5, fontName="Helvetica-Bold", textColor=NAVY, alignment=TA_RIGHT, leading=10)),
    ]
    earn_rows = [earn_header]
    for e in (slip.get("earnings") or []):
        earn_rows.append([
            Paragraph(e.get("label", ""), val),
            Paragraph(str(e.get("qty", "")), mono),
            Paragraph(str(e.get("unit", "")), mono),
            Paragraph(_idr(e.get("amount", 0)), ParagraphStyle("am_r", fontSize=7.5, fontName="Courier", textColor=BLACK, alignment=TA_RIGHT, leading=10)),
        ])
    # overtime row
    if slip.get("overtime_amount", 0) > 0:
        earn_rows.append([
            Paragraph(f"Uang Lembur ({slip.get('overtime_hours', 0)} jam × {_idr(slip.get('overtime_rate', 0))})", val),
            Paragraph("", val),
            Paragraph("", val),
            Paragraph(_idr(slip.get("overtime_amount", 0)), ParagraphStyle("am_r2", fontSize=7.5, fontName="Courier", textColor=BLACK, alignment=TA_RIGHT, leading=10)),
        ])
    earn_tbl = Table(earn_rows, colWidths=[W * 0.47, W * 0.13, W * 0.14, W * 0.26])
    earn_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  TEAL),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("ROWBACKGROUND",(0, 1), (-1, -1), None),
        ("ROWBACKGROUND",(0, 1), (-1, -1), LIGHT),
        ("ROWBACKGROUND",(0, 2), (-1, -2), WHITE),
        ("BOX",          (0, 0), (-1, -1), 0.5, TEAL),
        ("LINEBELOW",    (0, 0), (-1, 0),  0.5, TEAL),
        ("GRID",         (0, 1), (-1, -1), 0.2, colors.HexColor("#d1e4ed")),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))

    # earnings subtotal row
    earn_sub = Table(
        [[
            Paragraph("Total Pendapatan", ParagraphStyle("sub_l", fontSize=8, fontName="Helvetica-Bold", textColor=TEAL, leading=10)),
            Paragraph(_idr(slip.get("gross_pay", 0)), ParagraphStyle("sub_r", fontSize=8, fontName="Courier-Bold", textColor=TEAL, alignment=TA_RIGHT, leading=10)),
        ]],
        colWidths=[W * 0.74, W * 0.26],
    )
    earn_sub.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), colors.HexColor("#dbeaf4")),
        ("BOX",          (0, 0), (-1, -1), 0.5, TEAL),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))

    # ── allowances table (DA tunjangan tetap) ──────────────────────────────────
    allowance_items_data = slip.get("allowances") or []
    allowance_elements = []
    if allowance_items_data:
        alw_header = [
            Paragraph("Tunjangan", ParagraphStyle("ah_l", fontSize=7.5, fontName="Helvetica-Bold", textColor=WHITE, leading=10)),
            Paragraph("Jumlah", ParagraphStyle("ah_r", fontSize=7.5, fontName="Helvetica-Bold", textColor=WHITE, alignment=TA_RIGHT, leading=10)),
        ]
        alw_rows = [alw_header]
        for alw in allowance_items_data:
            alw_rows.append([
                Paragraph(alw.get("label", ""), val),
                Paragraph(_idr(alw.get("amount", 0)), ParagraphStyle("alw_r", fontSize=7.5, fontName="Courier", textColor=GREEN, alignment=TA_RIGHT, leading=10)),
            ])
        alw_tbl = Table(alw_rows, colWidths=[W * 0.74, W * 0.26])
        alw_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0),  colors.HexColor("#1a7a4a")),
            ("ROWBACKGROUND",(0, 1), (-1, -1), colors.HexColor("#f0faf5")),
            ("BOX",          (0, 0), (-1, -1), 0.5, colors.HexColor("#1a7a4a")),
            ("GRID",         (0, 1), (-1, -1), 0.2, colors.HexColor("#b0e0c0")),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",   (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
            ("LEFTPADDING",  (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        allowance_elements = [Spacer(1, 3 * mm), alw_tbl]

    # ── deductions table ────────────────────────────────────────────────────────
    ded_rows_data = slip.get("deductions") or []
    ded_elements = []
    if ded_rows_data:
        ded_header = [
            Paragraph("Potongan", ParagraphStyle("dh_l", fontSize=7.5, fontName="Helvetica-Bold", textColor=WHITE, leading=10)),
            Paragraph("Jumlah", ParagraphStyle("dh_r", fontSize=7.5, fontName="Helvetica-Bold", textColor=WHITE, alignment=TA_RIGHT, leading=10)),
        ]
        ded_rows = [ded_header]
        for d in ded_rows_data:
            ded_rows.append([
                Paragraph(d.get("label", ""), val),
                Paragraph(_idr(d.get("amount", 0)), ParagraphStyle("dr_r", fontSize=7.5, fontName="Courier", textColor=RED, alignment=TA_RIGHT, leading=10)),
            ])
        ded_tbl = Table(ded_rows, colWidths=[W * 0.74, W * 0.26])
        ded_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0),  colors.HexColor("#c0392b")),
            ("ROWBACKGROUND",(0, 1), (-1, -1), colors.HexColor("#fff5f5")),
            ("BOX",          (0, 0), (-1, -1), 0.5, colors.HexColor("#c0392b")),
            ("GRID",         (0, 1), (-1, -1), 0.2, colors.HexColor("#fcc")),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",   (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
            ("LEFTPADDING",  (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        ded_elements = [Spacer(1, 3 * mm), ded_tbl]

    # ── net pay box ─────────────────────────────────────────────────────────────
    net_tbl = Table(
        [[
            Paragraph("GAJI BERSIH", net_lbl),
            Paragraph(_idr(slip.get("net_pay", 0)), net_style),
        ]],
        colWidths=[W * 0.45, W * 0.55],
    )
    net_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), NAVY),
        ("BOX",          (0, 0), (-1, -1), 0,   NAVY),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [3]),
    ]))

    # ── attendance summary bar ──────────────────────────────────────────────────
    att_cells = [
        [Paragraph("Hadir", h3), Paragraph(str(slip.get("days_hadir", 0)), lbl)],
        [Paragraph("Jam Kerja", h3), Paragraph(f"{slip.get('total_hours_worked', 0)} j", lbl)],
        [Paragraph("Lembur", h3), Paragraph(f"{slip.get('overtime_hours', 0)} j", lbl)],
    ]
    att_bar = Table(
        [list(sum(att_cells, []))],
        colWidths=[W / 6] * 6,
    )
    att_bar.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), colors.HexColor("#f0f6fa")),
        ("BOX",          (0, 0), (-1, -1), 0.3, TEAL),
        ("GRID",         (0, 0), (-1, -1), 0.2, colors.HexColor("#c0d8e8")),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
    ]))

    # ── notes ───────────────────────────────────────────────────────────────────
    notes_el = []
    if slip.get("notes"):
        notes_el = [
            Spacer(1, 2 * mm),
            Paragraph(f"<i>Catatan: {slip['notes']}</i>", h3),
        ]

    # ── signature section ───────────────────────────────────────────────────────
    sig_tbl = Table(
        [[
            Paragraph("Disetujui oleh,", h3),
            Paragraph("Diterima oleh,", h3),
        ],
        [Spacer(1, 12 * mm), Spacer(1, 12 * mm)],
        [
            Paragraph("(________________)<br/><font size='6'>Manager / HRD</font>", ParagraphStyle("sig_l", fontSize=7, fontName="Helvetica", textColor=GREY, alignment=TA_CENTER, leading=9)),
            Paragraph(f"({slip.get('employee_name', '________________')})<br/><font size='6'>Karyawan</font>", ParagraphStyle("sig_r", fontSize=7, fontName="Helvetica", textColor=GREY, alignment=TA_CENTER, leading=9)),
        ]],
        colWidths=[W / 2, W / 2],
    )
    sig_tbl.setStyle(TableStyle([
        ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]))

    # ── assemble ────────────────────────────────────────────────────────────────
    story = [
        company_tbl,
        sub_tbl,
        HRFlowable(width="100%", thickness=1.5, color=TEAL, spaceAfter=4),
        emp_tbl,
        Spacer(1, 3 * mm),
        earn_tbl,
        earn_sub,
        *allowance_elements,
        *ded_elements,
        Spacer(1, 3 * mm),
        net_tbl,
        Spacer(1, 3 * mm),
        att_bar,
        *notes_el,
        Spacer(1, 5 * mm),
        HRFlowable(width="100%", thickness=0.5, color=GREY, spaceAfter=4),
        sig_tbl,
        Spacer(1, 2 * mm),
        Paragraph(
            f"<i>Slip ini dicetak secara otomatis oleh Sistem ERP CV. Dewi Aditya · {_now().strftime('%d/%m/%Y %H:%M')}</i>",
            ParagraphStyle("foot", fontSize=5.5, fontName="Helvetica-Oblique", textColor=GREY, alignment=TA_CENTER, leading=7)
        ),
    ]

    # ── watermark RAHASIA (diagonal, light grey) ──────────────────────────────
    def _rahasia_watermark(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 70)
        try:
            canvas.setFillColorRGB(0.82, 0.82, 0.82, alpha=0.30)
        except TypeError:
            # older reportlab — no alpha param
            canvas.setFillColorRGB(0.88, 0.88, 0.88)
        canvas.translate(A5[0] / 2, A5[1] / 2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, "RAHASIA")
        canvas.restoreState()

    doc.build(story, onFirstPage=_rahasia_watermark, onLaterPages=_rahasia_watermark)
    buf.seek(0)
    return buf


@router.get("/payslips/{pid}/pdf")
async def export_payslip_pdf(pid: str, request: Request):
    """Download PDF untuk satu slip gaji. Hanya HR/Admin/Manager yang bisa download. Karyawan lihat via UI saja."""
    user = await require_auth(request)
    db = get_db()
    role = (user.get("role") or "").lower()
    slip = await db.rahaza_payslips.find_one({"id": pid}, {"_id": 0})
    if not slip:
        raise HTTPException(404, "Payslip tidak ditemukan.")

    # Role check: hanya HR/admin/manager yang bisa download PDF
    can_download = role in ("superadmin", "admin", "owner", "hr", "manager")
    # Karyawan hanya bisa akses slip miliknya sendiri, dan TIDAK dapat download PDF
    if not can_download:
        emp = await db.rahaza_employees.find_one({"id": user.get("employee_id")}, {"_id": 0})
        if not emp or emp.get("id") != slip.get("employee_id"):
            raise HTTPException(403, "Anda tidak memiliki akses untuk mengunduh slip gaji ini.")
        # Employee view only - redirect to JSON view
        raise HTTPException(403, "Karyawan hanya bisa melihat slip gaji melalui Portal Saya. Hubungi HR untuk salinan resmi.")

    run = await db.rahaza_payroll_runs.find_one({"id": slip.get("run_id", "")}, {"_id": 0}) or {}
    try:
        buf = _build_payslip_pdf(dict(slip), dict(run))
    except Exception as e:
        log.error(f"PDF generation error: {e}", exc_info=True)
        raise HTTPException(500, f"Gagal generate PDF: {e}")
    fname = f"slip_{slip.get('employee_code', 'EMP')}_{slip.get('period_from', '')}_{slip.get('period_to', '')}.pdf"
    fname = fname.replace(" ", "_")
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/payroll-runs/{run_id}/pdf")
async def export_run_pdf(run_id: str, request: Request):
    """Download PDF bundle berisi SEMUA slip gaji dalam satu run (1 halaman per karyawan)."""
    await require_auth(request)
    db = get_db()
    run = await db.rahaza_payroll_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Payroll run tidak ditemukan.")
    payslips = await db.rahaza_payslips.find(
        {"run_id": run_id}, {"_id": 0}
    ).sort("employee_code", 1).to_list(500)
    if not payslips:
        raise HTTPException(404, "Tidak ada payslip dalam run ini.")

    try:
        from PyPDF2 import PdfWriter, PdfReader
        writer = PdfWriter()
        for slip in payslips:
            single_buf = _build_payslip_pdf(dict(slip), dict(run))
            reader = PdfReader(single_buf)
            for page in reader.pages:
                writer.add_page(page)
        out_buf = io.BytesIO()
        writer.write(out_buf)
        out_buf.seek(0)
    except ImportError:
        # Fallback: merge via concatenation into one buffer per-slip
        # Generate each slip separately and concatenate raw PDF bytes as ZIP
        import zipfile
        out_buf = io.BytesIO()
        with zipfile.ZipFile(out_buf, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for slip in payslips:
                single_buf = _build_payslip_pdf(dict(slip), dict(run))
                fname = f"slip_{slip.get('employee_code', 'EMP')}.pdf"
                zf.writestr(fname, single_buf.read())
        out_buf.seek(0)
        run_num = run.get("run_number", run_id[:8])
        return StreamingResponse(
            out_buf,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="payroll_{run_num}_slips.zip"'},
        )

    run_num = run.get("run_number", run_id[:8])
    fname = f"payroll_{run_num}_all_slips.pdf"
    return StreamingResponse(
        out_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ── PAYSLIPS ──────────────────────────────────────────────────────────────────
@router.get("/payslips")
async def list_payslips(request: Request, run_id: Optional[str] = None, employee_id: Optional[str] = None):
    await require_auth(request)
    db = get_db()
    q = {}
    if run_id: q["run_id"] = run_id
    if employee_id: q["employee_id"] = employee_id
    rows = await db.rahaza_payslips.find(q, {"_id": 0}).sort("employee_code", 1).to_list(500)
    return serialize_doc(rows)


@router.get("/payslips/{pid}")
async def get_payslip(pid: str, request: Request):
    await require_auth(request)
    db = get_db()
    row = await db.rahaza_payslips.find_one({"id": pid}, {"_id": 0})
    if not row:
        raise HTTPException(404, "Payslip tidak ditemukan.")
    return serialize_doc(row)


@router.put("/payslips/{pid}")
async def update_payslip(pid: str, request: Request):
    """Update deductions & notes saja (untuk adjust manual). Hanya jika run masih draft."""
    user = await _require_hr(request)
    db = get_db()
    slip = await db.rahaza_payslips.find_one({"id": pid}, {"_id": 0})
    if not slip:
        raise HTTPException(404, "Payslip tidak ditemukan.")
    run = await db.rahaza_payroll_runs.find_one({"id": slip["run_id"]}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Run induk tidak ditemukan.")
    if run.get("status") != "draft":
        raise HTTPException(400, "Run sudah di-finalize — slip tidak bisa diubah.")

    body = await request.json()
    deductions = body.get("deductions") or []
    norm_ded = []
    for d in deductions:
        label = (d.get("label") or "").strip()
        amount = float(d.get("amount") or 0)
        if not label or amount <= 0:
            continue
        norm_ded.append({"label": label, "amount": round(amount)})
    ded_total = sum(d["amount"] for d in norm_ded)
    gross = slip.get("gross_pay", 0)
    net = max(0, gross - ded_total)
    await db.rahaza_payslips.update_one({"id": pid}, {"$set": {
        "deductions": norm_ded,
        "deductions_total": ded_total,
        "net_pay": net,
        "notes": body.get("notes") or slip.get("notes", ""),
        "updated_at": _now(),
        "updated_by": user["id"],
        "updated_by_name": user.get("name", ""),
    }})
    out = await db.rahaza_payslips.find_one({"id": pid}, {"_id": 0})
    return serialize_doc(out)
