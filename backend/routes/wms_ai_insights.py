"""
WMS AI Insights — AI-powered analytics untuk WMS modules
Powered by GPT-4o via Emergent Universal Key
"""
import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from database import get_db
from auth import require_auth, serialize_doc
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wms/ai", tags=["wms-ai-insights"])

# Get Emergent Universal Key
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

# Initialize OpenAI with Emergent Universal Key
try:
    from openai import OpenAI
    client = OpenAI(
        api_key=EMERGENT_LLM_KEY,
        base_url="https://api.openai.com/v1"
    )
    logger.info("✅ OpenAI initialized with Emergent Universal Key")
except Exception as e:
    logger.warning(f"⚠️ OpenAI initialization failed: {e}")
    client = None


class QualityAnalysisRequest(BaseModel):
    roll_ids: list[str] = []
    time_period_days: int = 30


class MaterialRecommendationRequest(BaseModel):
    cmt_partner_id: str
    material_type: Optional[str] = None


class VariancePredictionRequest(BaseModel):
    zone_ids: list[str] = []
    cycle_type: str = "full"


def call_gpt4o(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    """Call GPT-4o via Emergent Universal Key"""
    if not client:
        raise HTTPException(500, "AI service not available")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"GPT-4o error: {e}")
        raise HTTPException(500, f"AI analysis failed: {str(e)}")


@router.post("/fabric-rolls/quality-analysis")
async def analyze_fabric_quality_patterns(data: QualityAnalysisRequest, request: Request):
    """
    AI-powered quality pattern analysis untuk fabric rolls
    Analyze QC rejection patterns dan suggest root causes
    """
    await require_auth(request)
    db = get_db()
    
    # Fetch fabric rolls data
    query = {"qc_status": {"$in": ["partial", "reject"]}}
    if data.roll_ids:
        query["id"] = {"$in": data.roll_ids}
    
    rolls = await db.wh_fabric_rolls.find(query).limit(100).to_list(100)
    
    if not rolls:
        return {
            "analysis": "Tidak ada data QC rejection yang cukup untuk dianalisis.",
            "insights": [],
            "recommendations": []
        }
    
    # Prepare data summary for AI
    rejection_summary = {}
    for roll in rolls:
        key = f"{roll.get('supplier_name', 'Unknown')} - {roll.get('color', 'N/A')}"
        if key not in rejection_summary:
            rejection_summary[key] = {"count": 0, "materials": set()}
        rejection_summary[key]["count"] += 1
        rejection_summary[key]["materials"].add(roll.get('material_name', 'Unknown'))
    
    # Convert sets to lists for JSON serialization
    summary_text = "\n".join([
        f"- {supplier}: {data['count']} rejections ({', '.join(list(data['materials']))})"
        for supplier, data in rejection_summary.items()
    ])
    
    system_prompt = """Anda adalah AI expert dalam quality control untuk industri garment textile.
Analisis pola rejection fabric rolls dan berikan insights yang actionable dalam Bahasa Indonesia.
Format output:
1. Root cause analysis (3-5 poin)
2. Actionable recommendations (3-5 poin)
3. Risk prediction untuk batch berikutnya"""
    
    user_prompt = f"""Analisis data rejection fabric rolls berikut:

Total rolls rejected: {len(rolls)}
Period: {data.time_period_days} hari terakhir

Breakdown per supplier & material:
{summary_text}

Berikan analisis komprehensif tentang:
1. Pattern yang terdeteksi
2. Kemungkinan root cause
3. Rekomendasi untuk supplier dan QC team"""
    
    ai_analysis = call_gpt4o(system_prompt, user_prompt, temperature=0.3)
    
    return {
        "analysis": ai_analysis,
        "data_summary": {
            "total_rejections": len(rolls),
            "affected_suppliers": len(rejection_summary),
            "period_days": data.time_period_days
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/cmt-dispatches/smart-recommendations")
async def get_smart_material_recommendations(data: MaterialRecommendationRequest, request: Request):
    """
    AI-powered material recommendations untuk CMT partner
    Based on historical dispatch success rate dan material compatibility
    """
    await require_auth(request)
    db = get_db()
    
    # Fetch historical dispatches for this CMT partner
    dispatches = await db.wh_cmt_dispatches.find({
        "cmt_partner_id": data.cmt_partner_id,
        "status": {"$in": ["completed", "dispatched"]}
    }).limit(50).to_list(50)
    
    if len(dispatches) < 3:
        return {
            "recommendations": [],
            "message": "Data historis belum cukup untuk memberikan rekomendasi AI. Minimum 3 dispatch diperlukan.",
            "confidence": "low"
        }
    
    # Analyze historical data
    material_stats = {}
    for dispatch in dispatches:
        mat = dispatch.get('material_name', 'Unknown')
        if mat not in material_stats:
            material_stats[mat] = {
                "total_sent": 0,
                "total_returned": 0,
                "dispatch_count": 0
            }
        material_stats[mat]["total_sent"] += dispatch.get('qty_sent', 0)
        material_stats[mat]["total_returned"] += dispatch.get('qty_returned', 0)
        material_stats[mat]["dispatch_count"] += 1
    
    # Calculate success rate
    for mat, stats in material_stats.items():
        if stats["total_sent"] > 0:
            stats["return_rate"] = (stats["total_returned"] / stats["total_sent"]) * 100
            stats["success_score"] = 100 - stats["return_rate"]
    
    stats_text = "\n".join([
        f"- {mat}: {stats['dispatch_count']}x dispatch, return rate {stats.get('return_rate', 0):.1f}%"
        for mat, stats in material_stats.items()
    ])
    
    system_prompt = """Anda adalah AI expert dalam supply chain management untuk garment manufacturing.
Berikan rekomendasi material terbaik untuk CMT partner berdasarkan historical performance.
Output dalam Bahasa Indonesia, format JSON-like list dengan reasoning."""
    
    user_prompt = f"""Analisis historical dispatch data untuk CMT partner:

Partner ID: {data.cmt_partner_id}
Total dispatches: {len(dispatches)}

Material performance:
{stats_text}

Berikan 3-5 rekomendasi material terbaik dengan alasan mengapa material tersebut cocok untuk partner ini.
Pertimbangkan: return rate, frequency, dan consistency."""
    
    ai_recommendations = call_gpt4o(system_prompt, user_prompt, temperature=0.5)
    
    # Get top materials by success score
    top_materials = sorted(
        [(mat, stats) for mat, stats in material_stats.items()],
        key=lambda x: x[1].get('success_score', 0),
        reverse=True
    )[:5]
    
    return {
        "ai_analysis": ai_recommendations,
        "top_materials": [
            {
                "material_name": mat,
                "dispatch_count": stats["dispatch_count"],
                "return_rate": round(stats.get("return_rate", 0), 2),
                "success_score": round(stats.get("success_score", 0), 2)
            }
            for mat, stats in top_materials
        ],
        "confidence": "high" if len(dispatches) >= 10 else "medium",
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/opname/predict-variances")
async def predict_cycle_variances(data: VariancePredictionRequest, request: Request):
    """
    AI-powered variance prediction untuk cycle counting
    Prediksi area/material mana yang kemungkinan besar ada variance
    """
    await require_auth(request)
    db = get_db()
    
    # Fetch historical cycles with variances
    cycles = await db.wh_opname2_cycles.find({
        "status": "completed",
        "variance_count": {"$gt": 0}
    }).sort("completed_at", -1).limit(20).to_list(20)
    
    if not cycles:
        return {
            "predictions": [],
            "message": "Belum ada data historical variance untuk prediksi",
            "confidence": "low"
        }
    
    # Analyze variance patterns
    variance_by_zone = {}
    total_variances = 0
    
    for cycle in cycles:
        cycle_id = cycle.get('id')
        # Fetch variances for this cycle
        variances = await db.wh_opname2_variances.find({"cycle_id": cycle_id}).to_list(100)
        
        for var in variances:
            zone = var.get('zone_id', 'Unknown')
            if zone not in variance_by_zone:
                variance_by_zone[zone] = {"count": 0, "materials": set()}
            variance_by_zone[zone]["count"] += 1
            variance_by_zone[zone]["materials"].add(var.get('material_name', 'Unknown'))
            total_variances += 1
    
    variance_text = "\n".join([
        f"- Zone {zone}: {data['count']} variances ({len(data['materials'])} materials berbeda)"
        for zone, data in variance_by_zone.items()
    ])
    
    system_prompt = """Anda adalah AI expert dalam inventory management dan cycle counting.
Prediksi area/zona warehouse mana yang kemungkinan besar akan memiliki variance.
Output dalam Bahasa Indonesia dengan prioritas dan reasoning."""
    
    user_prompt = f"""Analisis historical variance data dari {len(cycles)} cycle terakhir:

Total variances detected: {total_variances}
Cycle type yang akan dilakukan: {data.cycle_type}

Breakdown variance per zone:
{variance_text}

Target zones untuk cycle baru: {', '.join(data.zone_ids) if data.zone_ids else 'All zones'}

Prediksi:
1. Zone mana yang high-risk untuk variance
2. Material type apa yang perlu extra attention
3. Recommended approach untuk minimize variance"""
    
    ai_prediction = call_gpt4o(system_prompt, user_prompt, temperature=0.4)
    
    # Calculate risk scores
    risk_zones = sorted(
        [(zone, data['count']) for zone, data in variance_by_zone.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    return {
        "ai_prediction": ai_prediction,
        "high_risk_zones": [
            {"zone_id": zone, "variance_count": count, "risk_level": "high" if count > 5 else "medium"}
            for zone, count in risk_zones
        ],
        "confidence": "high" if len(cycles) >= 10 else "medium",
        "based_on_cycles": len(cycles),
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health")
async def ai_health_check(request: Request):
    """Check if AI service is available"""
    await require_auth(request)
    return {
        "ai_service": "available" if client else "unavailable",
        "model": "gpt-4o",
        "provider": "OpenAI via Emergent Universal Key"
    }
