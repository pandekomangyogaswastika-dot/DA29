"""
Session 14 — P2 AI Features (Business Intelligence)

P2-1: AI Business Daily Summary
- POST /api/ai-business/daily-summary — Generate narrative business summary

P2-2: AI Revenue Forecast
- POST /api/ai-business/revenue-forecast — Forecast revenue trend

P2-4: AI Fraud Detection
- POST /api/ai-business/fraud-detection — Detect anomalies in transactions

P2-6: AI Production Optimizer
- POST /api/ai-business/production-optimize — Optimize production schedule
"""
import os
import uuid
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Request, Query, HTTPException
from pydantic import BaseModel, Field
from database import get_db
from auth import require_auth
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai-business", tags=["ai-business"])

LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
LLM_MODEL = ("openai", "gpt-5.1")


def _now():
    return datetime.now(timezone.utc)


def ok(data=None, meta=None):
    r = {"success": True}
    if data is not None:
        r["data"] = data
    if meta is not None:
        r["metadata"] = meta
    return r


async def _call_ai(system_msg: str, user_msg: str, session_tag: str) -> str:
    """Helper: call LLM and return text response."""
    if not LLM_KEY:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY tidak dikonfigurasi")
    chat = LlmChat(
        api_key=LLM_KEY,
        session_id=f"ai-business-{session_tag}-{uuid.uuid4().hex[:8]}",
        system_message=system_msg,
    ).with_model(*LLM_MODEL)
    response = await chat.send_message(UserMessage(text=user_msg))
    return response


def _serialize_for_json(obj):
    """Recursively convert non-JSON-serializable types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items() if k != "_id"}
    if isinstance(obj, list):
        return [_serialize_for_json(i) for i in obj]
    return obj


# ═══════════════════════════════════════════════════════════════════════════
#  P2-1: AI BUSINESS DAILY SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/daily-summary")
async def generate_daily_summary(
    request: Request,
    days: int = Query(1, description="Periode ringkasan (default 1 hari)"),
):
    """
    P2-1: AI Business Daily Summary.
    Aggregates key metrics then sends to AI for narrative analysis.
    """
    await require_auth(request)
    db = get_db()

    since = _now() - timedelta(days=days)
    since_str = since.isoformat()

    # --- Collect data ---
    # Production WOs
    total_wo = await db.production_work_orders.count_documents({"created_at": {"$gte": since_str}})
    completed_wo = await db.production_work_orders.count_documents({"status": "completed", "updated_at": {"$gte": since_str}})

    # Finance: invoices
    invoices = await db.rahaza_invoices.find(
        {"date": {"$gte": since_str}}, {"_id": 0, "total": 1, "status": 1}
    ).to_list(100)
    total_invoiced = sum(float(i.get("total", 0)) for i in invoices)
    paid_count = sum(1 for i in invoices if i.get("status") == "paid")

    # Maklon orders
    maklon_new = await db.dewi_maklon_orders.count_documents({"order_date": {"$gte": since_str}})
    maklon_done = await db.dewi_maklon_orders.count_documents({"stage": {"$in": ["completed", "invoiced"]}, "updated_at": {"$gte": since_str}})

    # HR: attendance
    att_issues = await db.rahaza_attendance.count_documents({"date": {"$gte": since.strftime("%Y-%m-%d")}, "status": {"$in": ["late", "absent"]}})

    # Live sessions
    sessions = await db.marketing_live_sessions.find({"session_date": {"$gte": since}}, {"_id": 0, "revenue": 1}).to_list(100)
    live_rev = sum(float(s.get("revenue", 0)) for s in sessions)

    # Stock alerts
    low_stock = await db.rahaza_materials.count_documents({"active": True, "$expr": {"$lt": ["$total_qty", "$reorder_point"]}})

    # Build data payload
    metrics = {
        "periode": f"{days} hari terakhir",
        "tanggal": _now().strftime("%d %B %Y"),
        "produksi": {"work_order_baru": total_wo, "work_order_selesai": completed_wo},
        "keuangan": {"invoice_baru": len(invoices), "invoice_lunas": paid_count, "total_invoiced_rp": total_invoiced},
        "maklon": {"order_masuk": maklon_new, "order_selesai": maklon_done},
        "sdm": {"isu_kehadiran": att_issues},
        "marketing": {"sesi_live": len(sessions), "revenue_live_rp": live_rev},
        "alert": {"stok_rendah": low_stock},
    }

    system_prompt = """Kamu adalah AI Business Analyst untuk CV. Dewi Aditya, perusahaan garmen di Indonesia.
Buat ringkasan bisnis harian yang profesional dalam Bahasa Indonesia.
Gunakan format:
1. 📅 Ringkasan Eksekutif (2-3 kalimat)
2. 🏭 Produksi & Maklon (highlight key numbers)
3. 💰 Keuangan (highlight revenue & invoice)
4. 👥 SDM (jika ada isu)
5. 📢 Marketing (sesi live & revenue)
6. ⚠️ Alert & Rekomendasi Tindakan (jika ada masalah)
Buat ringkasan yang insightful, bukan sekadar daftar angka."""

    user_prompt = f"Data bisnis hari ini:\n{json.dumps(metrics, ensure_ascii=False, indent=2)}"

    summary_text = await _call_ai(system_prompt, user_prompt, "daily-summary")

    # Save to DB
    doc = {
        "id": str(uuid.uuid4()),
        "type": "daily_summary",
        "period_days": days,
        "metrics": metrics,
        "summary": summary_text,
        "generated_at": _now().isoformat(),
    }
    await db.ai_business_summaries.insert_one(doc)

    return ok(data={"summary": summary_text, "metrics": metrics, "generated_at": doc["generated_at"]})


@router.get("/daily-summary/history")
async def get_summary_history(request: Request, limit: int = Query(10)):
    await require_auth(request)
    db = get_db()
    docs = await db.ai_business_summaries.find({"type": "daily_summary"}, {"_id": 0}).sort("generated_at", -1).limit(limit).to_list(limit)
    return ok(data=_serialize_for_json(docs))


# ═══════════════════════════════════════════════════════════════════════════
#  P2-2: AI REVENUE FORECAST
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/revenue-forecast")
async def revenue_forecast(
    request: Request,
    months: int = Query(3, description="Berapa bulan ke depan yang diprediksi"),
):
    """
    P2-2: AI Revenue Forecast.
    Analyze historical invoice data and predict revenue trend.
    """
    await require_auth(request)
    db = get_db()

    # Get last 6 months of invoice data
    since = _now() - timedelta(days=180)
    invoices = await db.rahaza_invoices.find(
        {"date": {"$gte": since.isoformat()}},
        {"_id": 0, "date": 1, "total": 1, "status": 1, "type": 1}
    ).sort("date", 1).to_list(1000)

    # Also get maklon billing
    maklon_inv = await db.dewi_maklon_orders.find(
        {"stage": "invoiced", "updated_at": {"$gte": since.isoformat()}},
        {"_id": 0, "updated_at": 1, "total_price": 1, "quantity": 1}
    ).to_list(500)

    # Live session revenue
    sessions = await db.marketing_live_sessions.find(
        {"session_date": {"$gte": since}},
        {"_id": 0, "session_date": 1, "revenue": 1}
    ).to_list(500)

    # Aggregate by month
    monthly = {}
    for inv in invoices:
        try:
            month = str(inv.get("date", ""))[:7]  # YYYY-MM
            if month:
                monthly.setdefault(month, {"invoice": 0, "maklon": 0, "live": 0})
                monthly[month]["invoice"] += float(inv.get("total", 0))
        except Exception:
            pass

    for m in maklon_inv:
        try:
            month = str(m.get("updated_at", ""))[:7]
            if month:
                monthly.setdefault(month, {"invoice": 0, "maklon": 0, "live": 0})
                monthly[month]["maklon"] += float(m.get("total_price", 0))
        except Exception:
            pass

    for s in sessions:
        try:
            dt = s.get("session_date")
            month = str(dt.isoformat() if isinstance(dt, datetime) else dt)[:7]
            if month:
                monthly.setdefault(month, {"invoice": 0, "maklon": 0, "live": 0})
                monthly[month]["live"] += float(s.get("revenue", 0))
        except Exception:
            pass

    monthly_summary = [
        {
            "month": m,
            "invoice_rp": round(v["invoice"]),
            "maklon_rp": round(v["maklon"]),
            "live_rp": round(v["live"]),
            "total_rp": round(v["invoice"] + v["maklon"] + v["live"]),
        }
        for m, v in sorted(monthly.items())
    ]

    system_prompt = """Kamu adalah AI Financial Analyst untuk CV. Dewi Aditya, perusahaan garmen.
Analisis data pendapatan historis dan buat prediksi revenue untuk bulan ke depan.
Format response HARUS berupa JSON dengan struktur:
{
  "analysis": "narasi analisis trend",
  "forecast_months": [
    {"month": "YYYY-MM", "predicted_rp": 12345678, "confidence": "high/medium/low", "notes": ""}
  ],
  "key_insights": ["insight 1", "insight 2", "insight 3"],
  "growth_trend": "growing/stable/declining",
  "recommendation": "rekomendasi strategi"
}"""

    user_prompt = f"""Data pendapatan historis 6 bulan terakhir:
{json.dumps(monthly_summary, ensure_ascii=False, indent=2)}

Buat prediksi untuk {months} bulan ke depan."""

    raw_response = await _call_ai(system_prompt, user_prompt, "revenue-forecast")

    # Try to parse JSON from AI response
    try:
        # Extract JSON from response
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        if start >= 0 and end > start:
            forecast_data = json.loads(raw_response[start:end])
        else:
            forecast_data = {"analysis": raw_response, "forecast_months": [], "key_insights": [], "recommendation": ""}
    except Exception:
        forecast_data = {"analysis": raw_response, "forecast_months": [], "key_insights": [], "recommendation": ""}

    return ok(data={
        "historical": monthly_summary,
        "forecast": forecast_data,
        "forecast_months": months,
    })


# ═══════════════════════════════════════════════════════════════════════════
#  P2-4: FRAUD DETECTION AI
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/fraud-detection")
async def fraud_detection(
    request: Request,
    days: int = Query(30, description="Periode analisis"),
):
    """
    P2-4: AI Fraud Detection.
    Analyze financial transactions for anomalies.
    """
    await require_auth(request)
    db = get_db()

    since = _now() - timedelta(days=days)
    since_str = since.isoformat()

    # Get recent invoices and payments
    invoices = await db.rahaza_invoices.find(
        {"date": {"$gte": since_str}},
        {"_id": 0, "id": 1, "date": 1, "total": 1, "status": 1, "vendor": 1, "customer": 1, "type": 1}
    ).to_list(500)

    payments = await db.rahaza_payments.find(
        {"date": {"$gte": since_str}},
        {"_id": 0, "id": 1, "date": 1, "amount": 1, "method": 1, "reference": 1}
    ).to_list(500)

    # Stock adjustments (large or unusual)
    adj = await db.warehouse_movements.find(
        {"created_at": {"$gte": since}, "movement_type": {"$in": ["adjustment", "reset"]}},
        {"_id": 0, "id": 1, "sku": 1, "qty": 1, "movement_type": 1, "created_by": 1, "created_at": 1}
    ).to_list(200)

    # Basic statistical anomaly detection
    invoice_totals = [float(i.get("total", 0)) for i in invoices if i.get("total")]
    avg_inv = sum(invoice_totals) / len(invoice_totals) if invoice_totals else 0
    std_inv = (sum((x - avg_inv) ** 2 for x in invoice_totals) / max(len(invoice_totals), 1)) ** 0.5

    # Flag invoices > 3 std deviations from mean
    anomalies = []
    for inv in invoices:
        total = float(inv.get("total", 0))
        if std_inv > 0 and abs(total - avg_inv) > 3 * std_inv:
            anomalies.append({"type": "invoice_anomaly", "id": inv.get("id"), "total": total, "expected_range": f"{round(avg_inv - 2*std_inv):,} - {round(avg_inv + 2*std_inv):,}"})

    # Large stock adjustments
    if adj:
        adj_qty = [abs(float(a.get("qty", 0))) for a in adj]
        avg_adj = sum(adj_qty) / len(adj_qty)
        for a in adj:
            if abs(float(a.get("qty", 0))) > avg_adj * 5:
                anomalies.append({"type": "large_stock_adjustment", "sku": a.get("sku"), "qty": a.get("qty")})

    system_prompt = """Kamu adalah AI Risk & Fraud Analyst untuk CV. Dewi Aditya.
Analisis data transaksi keuangan dan pergerakan stok untuk mendeteksi anomali atau potensi fraud.
Format response sebagai JSON:
{
  "risk_level": "low/medium/high",
  "anomalies_found": [{"type": "", "description": "", "severity": "low/medium/high", "recommendation": ""}],
  "patterns_detected": ["pattern 1", "pattern 2"],
  "overall_assessment": "narasi penilaian risiko",
  "recommended_actions": ["aksi 1", "aksi 2"]
}"""

    summary_data = {
        "periode_hari": days,
        "total_invoice": len(invoices),
        "total_pembayaran": len(payments),
        "total_adjustment_stok": len(adj),
        "anomali_statistik": anomalies[:10],
        "avg_invoice": round(avg_inv),
        "std_invoice": round(std_inv),
    }

    user_prompt = f"Data transaksi {days} hari terakhir:\n{json.dumps(summary_data, ensure_ascii=False, indent=2)}"

    raw_response = await _call_ai(system_prompt, user_prompt, "fraud-detect")

    try:
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        if start >= 0 and end > start:
            fraud_data = json.loads(raw_response[start:end])
        else:
            fraud_data = {"risk_level": "low", "overall_assessment": raw_response, "anomalies_found": anomalies, "recommended_actions": []}
    except Exception:
        fraud_data = {"risk_level": "low", "overall_assessment": raw_response, "anomalies_found": anomalies, "recommended_actions": []}

    return ok(data={
        "statistical_anomalies": anomalies,
        "ai_analysis": fraud_data,
        "period_days": days,
        "transaction_summary": summary_data,
    })


# ═══════════════════════════════════════════════════════════════════════════
#  P2-6: AI PRODUCTION OPTIMIZER
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/production-optimize")
async def production_optimize(
    request: Request,
):
    """
    P2-6: AI Production Optimizer.
    Analyze current WO backlog, capacity, and pending orders to suggest optimal scheduling.
    """
    await require_auth(request)
    db = get_db()

    # Current active work orders
    active_wo = await db.production_work_orders.find(
        {"status": {"$in": ["in_progress", "pending", "not_started"]}},
        {"_id": 0, "id": 1, "order_code": 1, "product_name": 1, "quantity": 1, "priority": 1,
         "target_date": 1, "status": 1, "stage": 1}
    ).sort("target_date", 1).to_list(50)

    # Active maklon orders
    maklon_active = await db.dewi_maklon_orders.find(
        {"stage": {"$in": ["confirmed", "material_ready", "cutting", "sewing", "qc"]}},
        {"_id": 0, "order_code": 1, "garment_type": 1, "quantity": 1, "deadline_date": 1, "stage": 1}
    ).sort("deadline_date", 1).to_list(50)

    # Available capacity (count active production employees)
    emp_count = await db.rahaza_employees.count_documents({"employment_status": "active", "department": {"$in": ["Produksi", "Production", "Jahit"]}})

    # Material availability check
    low_mat = await db.rahaza_materials.count_documents(
        {"active": True, "$expr": {"$lt": ["$total_qty", {"$ifNull": ["$min_stock", 0]}]}}
    )

    data = {
        "work_orders_aktif": len(active_wo),
        "maklon_orders_aktif": len(maklon_active),
        "karyawan_produksi": emp_count,
        "material_kritis": low_mat,
        "wo_details": _serialize_for_json(active_wo[:10]),
        "maklon_details": _serialize_for_json(maklon_active[:10]),
    }

    system_prompt = """Kamu adalah AI Production Planner untuk CV. Dewi Aditya, pabrik garmen.
Analisis backlog produksi saat ini dan berikan rekomendasi penjadwalan optimal.
Format response sebagai JSON:
{
  "capacity_status": "over/normal/under",
  "bottlenecks": ["bottleneck 1", "bottleneck 2"],
  "priority_orders": [{"order_code": "", "reason": "", "suggested_start": ""}],
  "scheduling_suggestions": ["saran 1", "saran 2", "saran 3"],
  "material_concerns": ["concern 1"],
  "overall_assessment": "narasi penilaian kapasitas dan jadwal",
  "efficiency_score": 75
}"""

    user_prompt = f"Status produksi saat ini:\n{json.dumps(data, ensure_ascii=False, indent=2)}"

    raw_response = await _call_ai(system_prompt, user_prompt, "prod-optimize")

    try:
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        if start >= 0 and end > start:
            opt_data = json.loads(raw_response[start:end])
        else:
            opt_data = {"capacity_status": "normal", "overall_assessment": raw_response, "scheduling_suggestions": []}
    except Exception:
        opt_data = {"capacity_status": "normal", "overall_assessment": raw_response, "scheduling_suggestions": []}

    return ok(data={
        "current_state": data,
        "optimization": opt_data,
    })
