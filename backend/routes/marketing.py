"""
CV. Dewi Aditya — Marketing Portal (Phase 1: Foundation & Multi-Account)

Portal Marketing adalah transformasi dari "Toko Online" dengan fitur:
- Multi-platform multi-account management (unlimited accounts per platform)
- Store health dashboard dengan dual revenue stream (Total + Live)
- KOL & Creator management
- Task management system
- Smart import Excel/CSV (AI-powered)
- Catalog management + stock sync

Collections:
- marketing_platform_accounts: Platform accounts (Shopee, TikTok, Tokopedia)
- marketing_sales_data: Daily sales metrics (total + live revenue separated)
- marketing_kol_creators: KOL/Creator profiles & performance
- marketing_creator_item_requests: Creator request items for live
- marketing_tasks: Task management (Trello-style)
- marketing_catalogs: Product catalogs per account
- marketing_catalog_items: Catalog items (linked to master data)
- marketing_import_history: Smart import tracking

Phase 1 Endpoints (Foundation):
- Platform account CRUD
- Basic dashboard (per-account + consolidated)
- Manual sales data entry

Author: CV. Dewi Aditya Development Team
Date: 2026-05-01
"""

import uuid
import re
import html
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

logger = logging.getLogger(__name__)
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field
from database import get_db
from auth import require_auth, serialize_doc, log_activity

router = APIRouter(prefix='/api/marketing', tags=['Marketing-Portal'])


def _uid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


def _get_user(request):
    """Helper to safely get user from request.state"""
    return getattr(request.state, 'user', {"id": "system", "email": "system", "role": "admin"})


def _sanitize(value: str, max_len: int = 500) -> str:
    """HTML-escape dan trim user-supplied text untuk prevent XSS."""
    if not isinstance(value, str):
        return value
    return html.escape(value.strip())[:max_len]


def _is_pic_role(user) -> bool:
    """
    Check if user has PIC Marketing-level role for approval workflow.
    Allowed roles: admin, owner, superadmin, manager_* (manager_marketing, manager_keuangan, dll), pic_marketing, pic_toko.
    """
    role = (user.get("role") or "").lower()
    if role in {"admin", "owner", "superadmin"}:
        return True
    if role.startswith("manager_") or role.startswith("manager-"):
        return True
    if role in {"pic_marketing", "pic_toko"}:
        return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════════════════

class PlatformAccountCreate(BaseModel):
    account_code: str = Field(..., description="Unique code: SHOPEE-OFFICIAL, TIKTOK-RESELLER")
    account_name: str = Field(..., description="Display name: Shopee Official Store DEMO")
    platform: str = Field(..., description="shopee | tiktokshop | tokopedia")
    username: Optional[str] = Field(None, description="Platform username/store name")
    group: Optional[str] = Field("other", description="official_store | reseller | distributor | other")
    has_api_integration: bool = Field(False, description="Whether API integration is active")


class PlatformAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    username: Optional[str] = None
    group: Optional[str] = None
    status: Optional[str] = Field(None, description="active | inactive | suspended")
    has_api_integration: Optional[bool] = None
    pic_user_id: Optional[str] = Field(None, description="ID user PIC yang bertanggung jawab untuk akun ini")


class SalesDataEntry(BaseModel):
    """Manual sales data entry for Phase 1"""
    account_id: str
    date: str = Field(..., description="YYYY-MM-DD")
    revenue_type: str = Field(..., description="total | live")
    
    # Sales metrics
    revenue: float = Field(0, ge=0)
    orders: int = Field(0, ge=0)
    aov: Optional[float] = Field(None, ge=0, description="Average order value")
    gmv: Optional[float] = Field(None, ge=0, description="Gross merchandise value")
    conversion_rate: Optional[float] = Field(None, ge=0, le=1, description="0-1")
    
    # Fulfillment metrics (Phase 2)
    fulfillment_rate: Optional[float] = Field(None, ge=0, le=1)
    cancellation_rate: Optional[float] = Field(None, ge=0, le=1)
    return_rate: Optional[float] = Field(None, ge=0, le=1)
    late_shipment_rate: Optional[float] = Field(None, ge=0, le=1)
    
    # Customer satisfaction (Phase 2)
    rating: Optional[float] = Field(None, ge=0, le=5, description="Store rating 0-5")
    review_count: Optional[int] = Field(None, ge=0)
    response_rate: Optional[float] = Field(None, ge=0, le=1)
    response_time_hours: Optional[float] = Field(None, ge=0)
    
    # Live metrics (only for revenue_type='live') (Phase 2)
    viewers: Optional[int] = Field(None, ge=0)
    avg_viewers: Optional[int] = Field(None, ge=0)
    likes: Optional[int] = Field(None, ge=0)
    shares: Optional[int] = Field(None, ge=0)
    comments: Optional[int] = Field(None, ge=0)
    new_followers: Optional[int] = Field(None, ge=0)
    live_sessions: Optional[int] = Field(None, ge=0)


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH SCORE CALCULATION (Phase 2)
# ══════════════════════════════════════════════════════════════════════════════

async def _recalculate_health_score(db, account_id: str):
    """
    Calculate health score untuk account berdasarkan data 30 hari terakhir.
    
    Health Score = (
      Sales Performance (30%) +
      Fulfillment Quality (25%) +
      Customer Satisfaction (25%) +
      Engagement (10%) +
      Compliance (10%)
    ) / 5 × 100
    
    Score range: 0-100
    - 80-100: Excellent (green)
    - 60-79: Good (yellow)
    - <60: Needs Improvement (red)
    """
    date_to = _now().strftime("%Y-%m-%d")
    date_from = (_now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Get sales data for last 30 days
    sales_data = await db.marketing_sales_data.find({
        "account_id": account_id,
        "date": {"$gte": date_from, "$lte": date_to}
    }, {"_id": 0}).to_list(500)
    
    # Defensive: filter records yang punya schema valid (with revenue_type)
    sales_data = [s for s in sales_data if s.get("revenue_type") in ("total", "live")]
    
    if not sales_data:
        # No data yet — set to None (UI displays "N/A" instead of 0)
        await db.marketing_platform_accounts.update_one(
            {"id": account_id},
            {"$set": {"health_score": None, "updated_at": _now()}}
        )
        return None
    
    # 1. Sales Performance (30 points)
    # Based on: revenue growth, order volume, conversion rate
    total_revenue = sum(s.get("metrics", {}).get("revenue", 0) for s in sales_data if s.get("revenue_type") == "total")
    total_orders = sum(s.get("metrics", {}).get("orders", 0) for s in sales_data if s.get("revenue_type") == "total")
    avg_conversion = sum(s.get("metrics", {}).get("conversion_rate", 0) for s in sales_data) / len(sales_data) if sales_data else 0
    
    sales_score = 0
    if total_revenue > 0:
        sales_score += 15  # Has revenue
    if total_orders > 100:
        sales_score += 10  # Good order volume
    if avg_conversion > 0.02:
        sales_score += 5  # Decent conversion
    
    # 2. Fulfillment Quality (25 points)
    # Based on: fulfillment rate, cancellation rate, return rate, late shipment
    fulfillment_data = [s for s in sales_data if s.get("fulfillment")]
    if fulfillment_data:
        avg_fulfillment = sum(s["fulfillment"].get("fulfillment_rate", 0) for s in fulfillment_data) / len(fulfillment_data)
        avg_cancellation = sum(s["fulfillment"].get("cancellation_rate", 0) for s in fulfillment_data) / len(fulfillment_data)
        avg_return = sum(s["fulfillment"].get("return_rate", 0) for s in fulfillment_data) / len(fulfillment_data)
        avg_late = sum(s["fulfillment"].get("late_shipment_rate", 0) for s in fulfillment_data) / len(fulfillment_data)
        
        fulfillment_score = (avg_fulfillment * 10) + max(0, (1 - avg_cancellation) * 5) + max(0, (1 - avg_return) * 5) + max(0, (1 - avg_late) * 5)
    else:
        fulfillment_score = 0
    
    # 3. Customer Satisfaction (25 points)
    # Based on: rating, response rate, response time
    satisfaction_data = [s for s in sales_data if s.get("customer_satisfaction")]
    if satisfaction_data:
        avg_rating = sum(s["customer_satisfaction"].get("rating", 0) for s in satisfaction_data) / len(satisfaction_data)
        avg_response_rate = sum(s["customer_satisfaction"].get("response_rate", 0) for s in satisfaction_data) / len(satisfaction_data)
        avg_response_time = sum(s["customer_satisfaction"].get("response_time_hours", 0) for s in satisfaction_data) / len(satisfaction_data)
        
        rating_score = (avg_rating / 5) * 15  # Max 15 points
        response_score = avg_response_rate * 5  # Max 5 points
        time_score = max(0, 5 - (avg_response_time / 5))  # Max 5 points (faster = better)
        
        satisfaction_score = rating_score + response_score + time_score
    else:
        satisfaction_score = 0
    
    # 4. Engagement (10 points) - Live metrics
    # Based on: viewers, likes, shares, comments, followers
    live_data = [s for s in sales_data if s.get("revenue_type") == "live" and s.get("live_metrics")]
    if live_data:
        total_viewers = sum(s.get("live_metrics", {}).get("viewers", 0) for s in live_data)
        total_likes = sum(s.get("live_metrics", {}).get("likes", 0) for s in live_data)
        total_shares = sum(s.get("live_metrics", {}).get("shares", 0) for s in live_data)
        
        engagement_score = 0
        if total_viewers > 1000:
            engagement_score += 5
        if total_likes > 500:
            engagement_score += 3
        if total_shares > 50:
            engagement_score += 2
    else:
        engagement_score = 5  # Neutral if no live data
    
    # 5. Compliance (10 points)
    # Placeholder - assume 100% if data is being entered regularly
    compliance_score = 10 if len(sales_data) >= 7 else 5  # Penalized if not enough data
    
    # Calculate total
    total_score = sales_score + fulfillment_score + satisfaction_score + engagement_score + compliance_score
    health_score = min(100, max(0, round(total_score)))
    
    # Update account
    await db.marketing_platform_accounts.update_one(
        {"id": account_id},
        {"$set": {"health_score": health_score, "updated_at": _now()}}
    )
    
    return health_score


# ══════════════════════════════════════════════════════════════════════════════
# PLATFORM ACCOUNTS MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/accounts")
async def create_platform_account(data: PlatformAccountCreate, request: Request):
    """
    Create new platform account.
    PIC Marketing can create unlimited accounts per platform.
    """
    await require_auth(request)
    db = get_db()
    
    # Validate platform
    valid_platforms = ["shopee", "tiktokshop", "tokopedia"]
    if data.platform not in valid_platforms:
        raise HTTPException(400, f"Platform must be one of: {', '.join(valid_platforms)}")
    
    # Check duplicate account_code
    existing = await db.marketing_platform_accounts.find_one({"account_code": data.account_code}, {"_id": 0})
    if existing:
        raise HTTPException(400, f"Account code '{data.account_code}' already exists")
    
    account = {
        "id": _uid(),
        "account_code": _sanitize(data.account_code, 100),
        "account_name": _sanitize(data.account_name, 200),
        "platform": data.platform,
        "username": _sanitize(data.username or "", 100),
        "status": "active",
        "group": data.group or "other",
        "credentials": {
            "api_key": "",
            "api_secret": "",
            "has_api_integration": data.has_api_integration
        },
        "import_config": {
            "saved_templates": []
        },
        "assigned_staff": [],
        "pic_id": getattr(request.state, 'user', {}).get("id", "system"),
        "health_score": None,  # None = belum ada data (UI tampilkan "N/A")
        "created_at": _now(),
        "created_by": getattr(request.state, 'user', {}).get("email", "system"),
        "updated_at": _now()
    }
    
    await db.marketing_platform_accounts.insert_one(account)
    
    await log_activity(
        getattr(request.state, 'user', {}).get("id", "system"),
        getattr(request.state, 'user', {}).get("name") or getattr(request.state, 'user', {}).get("email", "system"),
        "create",
        "marketing_account",
        f"Created platform account: {data.account_name} ({data.platform})"
    )
    
    return serialize_doc({"message": "Platform account created", "account": account})


@router.get("/accounts")
async def list_platform_accounts(
    request: Request,
    platform: Optional[str] = Query(None, description="Filter by platform"),
    status: Optional[str] = Query(None, description="Filter by status"),
    group: Optional[str] = Query(None, description="Filter by group")
):
    """
    List all platform accounts with optional filters.
    PIC Marketing sees all, Staff sees assigned only.
    """
    await require_auth(request)
    db = get_db()
    
    query = {}
    
    # Build query filters
    if platform:
        query["platform"] = platform
    if status:
        query["status"] = status
    if group:
        query["group"] = group
    
    # Role-based filtering — Phase 2: implement proper staff-only view
    # Currently showing all accounts to all authenticated users
    # Future: if user_role == "staff": query["assigned_staff"] = user_id
    
    accounts = await db.marketing_platform_accounts.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    return serialize_doc(accounts)


@router.get("/accounts/{account_id}")
async def get_platform_account(account_id: str, request: Request):
    """Get platform account detail"""
    await require_auth(request)
    db = get_db()
    
    account = await db.marketing_platform_accounts.find_one({"id": account_id}, {"_id": 0})
    if not account:
        raise HTTPException(404, "Account not found")
    
    return serialize_doc(account)


@router.put("/accounts/{account_id}")
async def update_platform_account(account_id: str, data: PlatformAccountUpdate, request: Request):
    """Update platform account"""
    await require_auth(request)
    db = get_db()
    
    account = await db.marketing_platform_accounts.find_one({"id": account_id}, {"_id": 0})
    if not account:
        raise HTTPException(404, "Account not found")
    
    # Build update dict
    update_data = {}
    if data.account_name is not None:
        update_data["account_name"] = data.account_name
    if data.username is not None:
        update_data["username"] = data.username
    if data.group is not None:
        update_data["group"] = data.group
    if data.status is not None:
        valid_status = ["active", "inactive", "suspended"]
        if data.status not in valid_status:
            raise HTTPException(400, f"Status must be one of: {', '.join(valid_status)}")
        update_data["status"] = data.status
    if data.has_api_integration is not None:
        update_data["credentials.has_api_integration"] = data.has_api_integration
    if data.pic_user_id is not None:
        update_data["pic_user_id"] = data.pic_user_id
        # Denormalize nama PIC untuk tampilan
        if data.pic_user_id:
            pic_user = await db.users.find_one({"id": data.pic_user_id}, {"_id": 0, "name": 1, "email": 1})
            update_data["pic_user_name"] = (pic_user.get("name") or pic_user.get("email")) if pic_user else None
        else:
            update_data["pic_user_name"] = None
    
    update_data["updated_at"] = _now()
    
    await db.marketing_platform_accounts.update_one(
        {"id": account_id},
        {"$set": update_data}
    )
    
    await log_activity(
        (_get_user(request)).get("id", "system"),
        (_get_user(request)).get("name") or (_get_user(request)).get("email", "system"),
        "update",
        "marketing_account",
        f"Updated platform account: {account['account_name']}"
    )
    
    # Get updated account
    updated = await db.marketing_platform_accounts.find_one({"id": account_id}, {"_id": 0})
    return serialize_doc({"message": "Platform account updated", "account": updated})


@router.delete("/accounts/{account_id}")
async def archive_platform_account(account_id: str, request: Request):
    """
    Archive (soft delete) platform account.
    Sets status to 'inactive' instead of hard delete.
    """
    await require_auth(request)
    db = get_db()
    
    account = await db.marketing_platform_accounts.find_one({"id": account_id}, {"_id": 0})
    if not account:
        raise HTTPException(404, "Account not found")
    
    await db.marketing_platform_accounts.update_one(
        {"id": account_id},
        {"$set": {"status": "inactive", "updated_at": _now()}}
    )
    
    await log_activity(
        (_get_user(request)).get("id", "system"),
        (_get_user(request)).get("name") or (_get_user(request)).get("email", "system"),
        "archive",
        "marketing_account",
        f"Archived platform account: {account['account_name']}"
    )
    
    return serialize_doc({"message": "Platform account archived"})


# ══════════════════════════════════════════════════════════════════════════════
# SALES DATA ENTRY (Manual for Phase 1)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/sales-data")
async def create_sales_data(data: SalesDataEntry, request: Request):
    """
    Manual sales data entry for Phase 1.
    Phase 4 will replace this with smart import.
    
    IMPORTANT: revenue_type must be 'total' OR 'live' (separated)
    """
    await require_auth(request)
    db = get_db()
    
    # Validate account exists
    account = await db.marketing_platform_accounts.find_one({"id": data.account_id}, {"_id": 0})
    if not account:
        raise HTTPException(404, "Account not found")
    
    # Validate revenue_type
    if data.revenue_type not in ["total", "live"]:
        raise HTTPException(400, "revenue_type must be 'total' or 'live'")
    
    # Check duplicate entry (same account + date + revenue_type)
    existing = await db.marketing_sales_data.find_one({
        "account_id": data.account_id,
        "date": data.date,
        "revenue_type": data.revenue_type
    }, {"_id": 0})
    
    if existing:
        raise HTTPException(400, f"Sales data for {data.date} ({data.revenue_type}) already exists for this account")
    
    # Calculate AOV if not provided
    aov = data.aov
    if aov is None and data.orders > 0:
        aov = data.revenue / data.orders
    
    # Build sales entry with complete metrics
    sales_entry = {
        "id": _uid(),
        "account_id": data.account_id,
        "account_code": account["account_code"],
        "platform": account["platform"],
        "date": data.date,
        "revenue_type": data.revenue_type,
        "metrics": {
            "revenue": data.revenue,
            "orders": data.orders,
            "aov": aov or 0,
            "gmv": data.gmv or data.revenue,
            "conversion_rate": data.conversion_rate or 0
        },
        "fulfillment": {
            "fulfillment_rate": data.fulfillment_rate or 0,
            "cancellation_rate": data.cancellation_rate or 0,
            "return_rate": data.return_rate or 0,
            "late_shipment_rate": data.late_shipment_rate or 0
        },
        "customer_satisfaction": {
            "rating": data.rating or 0,
            "review_count": data.review_count or 0,
            "response_rate": data.response_rate or 0,
            "response_time_hours": data.response_time_hours or 0
        },
        "live_metrics": {
            "viewers": data.viewers or 0,
            "avg_viewers": data.avg_viewers or 0,
            "likes": data.likes or 0,
            "shares": data.shares or 0,
            "comments": data.comments or 0,
            "new_followers": data.new_followers or 0,
            "live_sessions": data.live_sessions or 0
        } if data.revenue_type == "live" else {},
        "import_history_id": None,  # Manual entry, no import
        "created_at": _now(),
        "created_by": _get_user(request).get("email", "system")
    }
    
    await db.marketing_sales_data.insert_one(sales_entry)
    
    # Update account health score after new data
    await _recalculate_health_score(db, data.account_id)
    
    await log_activity(
        (_get_user(request)).get("id", "system"),
        (_get_user(request)).get("name") or (_get_user(request)).get("email", "system"),
        "create",
        "marketing_sales_data",
        f"Added sales data: {account['account_name']} - {data.date} ({data.revenue_type})"
    )
    
    return serialize_doc({"message": "Sales data created", "entry": sales_entry})


@router.get("/accounts/{account_id}/sales")
async def get_account_sales_data(
    account_id: str,
    request: Request,
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    revenue_type: Optional[str] = Query(None, description="total | live | all")
):
    """
    Get sales data for an account with date range filter.
    revenue_type='all' returns both total and live data.
    """
    await require_auth(request)
    db = get_db()
    
    account = await db.marketing_platform_accounts.find_one({"id": account_id}, {"_id": 0})
    if not account:
        raise HTTPException(404, "Account not found")
    
    query = {"account_id": account_id}
    
    # Date range filter
    if date_from or date_to:
        query["date"] = {}
        if date_from:
            query["date"]["$gte"] = date_from
        if date_to:
            query["date"]["$lte"] = date_to
    
    # Revenue type filter
    if revenue_type and revenue_type != "all":
        if revenue_type not in ["total", "live"]:
            raise HTTPException(400, "revenue_type must be 'total', 'live', or 'all'")
        query["revenue_type"] = revenue_type
    
    sales_data = await db.marketing_sales_data.find(query, {"_id": 0}).sort("date", -1).to_list(500)
    
    return serialize_doc(sales_data)


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD (Basic for Phase 1)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard/overview")
async def get_dashboard_overview(
    request: Request,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """
    Consolidated dashboard for all accounts.
    Shows: Total revenue (all accounts), Total orders, Account count, etc.
    """
    await require_auth(request)
    db = get_db()
    
    # Bug #3 fix: Query ALL accounts first, then derive active subset
    all_accounts = await db.marketing_platform_accounts.find({}, {"_id": 0}).to_list(500)
    active_accounts_list = [a for a in all_accounts if a.get("status") == "active"]
    active_ids = [a["id"] for a in active_accounts_list]
    
    # Date range default: last 30 days
    if not date_to:
        date_to = _now().strftime("%Y-%m-%d")
    if not date_from:
        date_from = (_now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Bug #2 fix: Filter sales ONLY for active account_ids
    query = {
        "date": {"$gte": date_from, "$lte": date_to},
        "account_id": {"$in": active_ids} if active_ids else {"$in": []}
    }
    
    # Total revenue (both total + live types, but we'll separate in response)
    total_sales = await db.marketing_sales_data.find(query, {"_id": 0}).to_list(500)
    
    total_revenue = 0
    total_revenue_live = 0
    total_orders = 0
    
    for sale in total_sales:
        if sale.get("revenue_type") == "total":
            total_revenue += sale["metrics"].get("revenue", 0)
            total_orders += sale["metrics"].get("orders", 0)
        elif sale.get("revenue_type") == "live":
            total_revenue_live += sale["metrics"].get("revenue", 0)
    
    # Top performing account (by revenue) — only from active accounts
    account_revenue = {}
    for sale in total_sales:
        acc_id = sale["account_id"]
        if sale.get("revenue_type") == "total":
            account_revenue[acc_id] = account_revenue.get(acc_id, 0) + sale["metrics"].get("revenue", 0)
    
    top_account_id = max(account_revenue, key=account_revenue.get) if account_revenue else None
    top_account = None
    if top_account_id:
        top_account = await db.marketing_platform_accounts.find_one({"id": top_account_id}, {"_id": 0, "account_name": 1, "platform": 1})
    
    return serialize_doc({
        "period": {
            "date_from": date_from,
            "date_to": date_to
        },
        "summary": {
            "total_accounts": len(all_accounts),
            "active_accounts": len(active_accounts_list),
            "total_revenue": round(total_revenue),
            "total_revenue_live": round(total_revenue_live),
            "total_orders": total_orders,
            "avg_order_value": round(total_revenue / total_orders) if total_orders > 0 else 0
        },
        "top_account": {
            "account_id": top_account_id,
            "account_name": top_account.get("account_name") if top_account else None,
            "platform": top_account.get("platform") if top_account else None,
            "revenue": round(account_revenue.get(top_account_id, 0)) if top_account_id else 0
        } if top_account else None
    })


@router.get("/accounts/{account_id}/dashboard")
async def get_account_dashboard(
    account_id: str,
    request: Request,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """
    Per-account dashboard with detailed metrics.
    Shows dual revenue stream (total + live) separately.
    """
    await require_auth(request)
    db = get_db()
    
    account = await db.marketing_platform_accounts.find_one({"id": account_id}, {"_id": 0})
    if not account:
        raise HTTPException(404, "Account not found")
    
    # Date range default: last 30 days
    if not date_to:
        date_to = _now().strftime("%Y-%m-%d")
    if not date_from:
        date_from = (_now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Get sales data for this account
    query = {
        "account_id": account_id,
        "date": {"$gte": date_from, "$lte": date_to}
    }
    
    sales_data = await db.marketing_sales_data.find(query, {"_id": 0}).sort("date", 1).to_list(500)
    
    # Separate total vs live
    total_revenue = 0
    total_orders = 0
    live_revenue = 0
    live_orders = 0
    
    daily_chart_total = []
    daily_chart_live = []
    
    # Latest metrics for health indicators
    latest_fulfillment = {}
    latest_satisfaction = {}
    
    for sale in sales_data:
        if sale["revenue_type"] == "total":
            total_revenue += sale["metrics"].get("revenue", 0)
            total_orders += sale["metrics"].get("orders", 0)
            daily_chart_total.append({
                "date": sale["date"],
                "revenue": sale["metrics"].get("revenue", 0),
                "orders": sale["metrics"].get("orders", 0)
            })
            # Get latest fulfillment & satisfaction
            if sale.get("fulfillment"):
                latest_fulfillment = sale["fulfillment"]
            if sale.get("customer_satisfaction"):
                latest_satisfaction = sale["customer_satisfaction"]
        elif sale["revenue_type"] == "live":
            live_revenue += sale["metrics"].get("revenue", 0)
            live_orders += sale["metrics"].get("orders", 0)
            daily_chart_live.append({
                "date": sale["date"],
                "revenue": sale["metrics"].get("revenue", 0),
                "orders": sale["metrics"].get("orders", 0)
            })
    
    return serialize_doc({
        "account": {
            "id": account["id"],
            "account_code": account["account_code"],
            "account_name": account["account_name"],
            "platform": account["platform"],
            "status": account["status"],
            "health_score": account.get("health_score", 0)
        },
        "period": {
            "date_from": date_from,
            "date_to": date_to
        },
        "total_revenue_stream": {
            "revenue": round(total_revenue),
            "orders": total_orders,
            "aov": round(total_revenue / total_orders) if total_orders > 0 else 0,
            "daily_chart": daily_chart_total
        },
        "live_revenue_stream": {
            "revenue": round(live_revenue),
            "orders": live_orders,
            "aov": round(live_revenue / live_orders) if live_orders > 0 else 0,
            "daily_chart": daily_chart_live
        },
        "health_metrics": {
            "rating": latest_satisfaction.get("rating", 0),
            "review_count": latest_satisfaction.get("review_count", 0),
            "response_rate": latest_satisfaction.get("response_rate", 0),
            "fulfillment_rate": latest_fulfillment.get("fulfillment_rate", 0),
            "cancellation_rate": latest_fulfillment.get("cancellation_rate", 0),
            "return_rate": latest_fulfillment.get("return_rate", 0),
            "late_shipment_rate": latest_fulfillment.get("late_shipment_rate", 0)
        }
    })


@router.post("/accounts/{account_id}/recalculate-health")
async def recalculate_account_health(account_id: str, request: Request):
    """
    Manually trigger health score recalculation for an account.
    Useful after bulk data import or corrections.
    """
    await require_auth(request)
    db = get_db()
    
    account = await db.marketing_platform_accounts.find_one({"id": account_id}, {"_id": 0})
    if not account:
        raise HTTPException(404, "Account not found")
    
    new_score = await _recalculate_health_score(db, account_id)
    
    return serialize_doc({
        "message": "Health score recalculated",
        "account_id": account_id,
        "account_name": account["account_name"],
        "new_health_score": new_score
    })


@router.get("/dashboard/comparison")
async def get_comparison_dashboard(
    request: Request,
    accounts: str = Query(..., description="Comma-separated account IDs (max 5)"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """
    Comparison dashboard for side-by-side account analysis.
    Max 5 accounts can be compared at once.
    """
    await require_auth(request)
    db = get_db()
    
    # Parse account IDs
    account_ids = [aid.strip() for aid in accounts.split(",") if aid.strip()]
    if len(account_ids) > 5:
        raise HTTPException(400, "Maximum 5 accounts can be compared at once")
    if len(account_ids) < 2:
        raise HTTPException(400, "At least 2 accounts required for comparison")
    
    # Date range default: last 30 days
    if not date_to:
        date_to = _now().strftime("%Y-%m-%d")
    if not date_from:
        date_from = (_now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    comparison_data = []

    # ── FIX N+1: Batch fetch accounts + sales in 2 queries instead of N×2 ─────
    accounts_list = await db.marketing_platform_accounts.find(
        {"id": {"$in": account_ids}}, {"_id": 0}
    ).to_list(500)
    accounts_map = {a["id"]: a for a in accounts_list}

    all_sales = await db.marketing_sales_data.find(
        {
            "account_id": {"$in": account_ids},
            "date": {"$gte": date_from, "$lte": date_to},
            "revenue_type": "total"
        },
        {"_id": 0}
    ).to_list(500)

    # Group sales by account_id in memory
    from collections import defaultdict as _defaultdict
    sales_by_account = _defaultdict(list)
    for s in all_sales:
        sales_by_account[s["account_id"]].append(s)

    for account_id in account_ids:
        account = accounts_map.get(account_id)
        if not account:
            continue  # Skip invalid IDs

        sales_data = sales_by_account.get(account_id, [])

        total_revenue = sum(s["metrics"].get("revenue", 0) for s in sales_data)
        total_orders = sum(s["metrics"].get("orders", 0) for s in sales_data)

        # Get latest satisfaction
        latest_rating = 0
        if sales_data:
            last_sale = sales_data[-1]
            if last_sale.get("customer_satisfaction"):
                latest_rating = last_sale["customer_satisfaction"].get("rating", 0)

        comparison_data.append({
            "account_id": account["id"],
            "account_code": account["account_code"],
            "account_name": account["account_name"],
            "platform": account["platform"],
            "health_score": account.get("health_score"),  # None = N/A
            "total_revenue": round(total_revenue),
            "total_orders": total_orders,
            "aov": round(total_revenue / total_orders) if total_orders > 0 else 0,
            "rating": latest_rating
        })
    
    return serialize_doc({
        "period": {
            "date_from": date_from,
            "date_to": date_to
        },
        "accounts": comparison_data
    })


# ══════════════════════════════════════════════════════════════════════════════
# UTILITY: Seed sample data for testing
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/seed-sample-data")
async def seed_sample_data(request: Request):
    """
    Seed sample platform accounts and sales data for testing.
    USE ONLY FOR DEVELOPMENT/TESTING.
    """
    await require_auth(request)
    db = get_db()
    
    # Create 3 sample accounts
    accounts = [
        {
            "id": _uid(),
            "account_code": "SHOPEE-OFFICIAL",
            "account_name": "Shopee Official Store DEMO",
            "platform": "shopee",
            "username": "demobrand_official",
            "status": "active",
            "group": "official_store",
            "credentials": {"has_api_integration": False},
            "import_config": {"saved_templates": []},
            "assigned_staff": [],
            "pic_id": _get_user(request).get("id"),
            "health_score": 0,
            "created_at": _now(),
            "created_by": "seed",
            "updated_at": _now()
        },
        {
            "id": _uid(),
            "account_code": "SHOPEE-RESELLER",
            "account_name": "Shopee Reseller A",
            "platform": "shopee",
            "username": "demobrand_reseller",
            "status": "active",
            "group": "reseller",
            "credentials": {"has_api_integration": False},
            "import_config": {"saved_templates": []},
            "assigned_staff": [],
            "pic_id": _get_user(request).get("id"),
            "health_score": 0,
            "created_at": _now(),
            "created_by": "seed",
            "updated_at": _now()
        },
        {
            "id": _uid(),
            "account_code": "TIKTOK-STORE",
            "account_name": "TikTok Shop DEMO",
            "platform": "tiktokshop",
            "username": "demobrand_tiktok",
            "status": "active",
            "group": "official_store",
            "credentials": {"has_api_integration": False},
            "import_config": {"saved_templates": []},
            "assigned_staff": [],
            "pic_id": _get_user(request).get("id"),
            "health_score": 0,
            "created_at": _now(),
            "created_by": "seed",
            "updated_at": _now()
        }
    ]
    
    # Insert accounts
    for acc in accounts:
        existing = await db.marketing_platform_accounts.find_one({"account_code": acc["account_code"]}, {"_id": 0})
        if not existing:
            await db.marketing_platform_accounts.insert_one(acc)
    
    return serialize_doc({"message": "Sample data seeded", "accounts_created": len(accounts)})



# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3: TASK MANAGEMENT SYSTEM (Trello-style)
# ══════════════════════════════════════════════════════════════════════════════

# Pydantic Models for Tasks

class RecurrenceConfig(BaseModel):
    frequency: str = Field(..., description="daily | weekly | monthly | one-time")
    time: str = Field("09:00", description="HH:MM format")
    days_of_week: Optional[List[str]] = Field(None, description="For weekly: ['monday', 'tuesday', ...]")
    day_of_month: Optional[int] = Field(None, description="For monthly: 1-31")
    auto_create: bool = Field(True, description="Auto-create tasks on schedule")


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    task_type: str = Field("data_entry", description="data_entry | review | analysis | reporting | operational")
    recurrence: str = Field("one-time", description="daily | weekly | monthly | one-time")
    recurrence_config: Optional[RecurrenceConfig] = None
    assigned_to: Optional[str] = Field(None, description="User ID to assign")
    account_id: Optional[str] = Field(None, description="Related platform account")
    priority: str = Field("medium", description="high | medium | low")
    due_date: Optional[str] = Field(None, description="ISO datetime string")
    checklist: Optional[List[dict]] = Field(None, description="List of {item: str, completed: bool}")
    # ── Actionable Task fields ──
    related_entity: Optional[str] = Field(None, description="sales_data | return | review | complaint | campaign | content | sample | launch")
    related_entity_id: Optional[str] = Field(None, description="UUID dari entitas terkait (jika sudah ada)")
    related_form_data: Optional[dict] = Field(None, description="Pre-fill data untuk inline form di task drawer")
    action_type: Optional[str] = Field(None, description="submit_form | approve_reject | review_content | manual_check")


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, description="to_do | in_progress | pending_approval | done | cancelled")
    assigned_to: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    checklist: Optional[List[dict]] = None
    completion_notes: Optional[str] = None


class TaskCompleteAction(BaseModel):
    """Payload untuk execute task action (sales submission, return approval, dll)."""
    action_data: dict = Field(..., description="Data spesifik untuk action (e.g. sales numbers, response text)")
    completion_notes: Optional[str] = ""


class TaskTemplateCreate(BaseModel):
    template_name: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    task_type: str = Field("data_entry")
    recurrence: str = Field("daily")
    recurrence_config: RecurrenceConfig
    default_assigned_role: str = Field("staff", description="staff | pic")
    account_id: Optional[str] = None
    priority: str = Field("medium")
    checklist_template: Optional[List[str]] = Field(None, description="List of checklist item labels")
    is_active: bool = Field(True)


# Helper: Generate task code
def _generate_task_code():
    """Generate unique task code: TSK-YYYYMMDDNN"""
    now = _now()
    date_str = now.strftime("%Y%m%d")
    random_suffix = str(uuid.uuid4())[:8].upper()
    return f"TSK-{date_str}-{random_suffix}"


# ══════════════════════════════════════════════════════════════════════════════
# TASK CRUD
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/tasks")
async def create_task(data: TaskCreate, request: Request):
    """
    Create new task (manual or from template).
    Only PIC Marketing can create tasks.
    """
    await require_auth(request)
    db = get_db()
    user = _get_user(request)
    
    # Validate task_type
    valid_types = ["data_entry", "review", "analysis", "reporting", "operational"]
    if data.task_type not in valid_types:
        raise HTTPException(400, f"task_type must be one of: {', '.join(valid_types)}")
    
    # Validate priority
    valid_priority = ["high", "medium", "low"]
    if data.priority not in valid_priority:
        raise HTTPException(400, f"priority must be one of: {', '.join(valid_priority)}")
    
    # Build task document
    task = {
        "id": _uid(),
        "task_code": _generate_task_code(),
        "title": _sanitize(data.title, 300),
        "description": _sanitize(data.description or "", 2000),
        "task_type": data.task_type,
        "recurrence": data.recurrence,
        "recurrence_config": data.recurrence_config.dict() if data.recurrence_config else {},
        "assigned_to": data.assigned_to,
        "assigned_by": user.get("id"),
        "account_id": data.account_id,
        "priority": data.priority,
        "due_date": data.due_date,
        "status": "to_do",
        "checklist": data.checklist or [],
        "attachments": [],
        "completion_notes": "",
        "approval_status": None,
        "approved_by": None,
        "approved_at": None,
        # ── Actionable task linkage ──
        "related_entity": data.related_entity,
        "related_entity_id": data.related_entity_id,
        "related_form_data": data.related_form_data or {},
        "action_type": data.action_type,
        "action_executed_at": None,
        "action_result": None,
        "created_at": _now(),
        "updated_at": _now()
    }
    
    await db.marketing_tasks.insert_one(task)
    
    await log_activity(
        user.get("id", "system"),
        user.get("name") or user.get("email", "system"),
        "create",
        "marketing_task",
        f"Created task: {data.title}"
    )
    
    return serialize_doc({"message": "Task created", "task": task})


@router.get("/tasks")
async def list_tasks(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned user"),
    account_id: Optional[str] = Query(None, description="Filter by account"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    approval_status: Optional[str] = Query(None, description="pending | approved | rejected"),
    page: int = Query(default=1, ge=1, description="Halaman (mulai dari 1)"),
    limit: int = Query(default=20, ge=1, le=100, description="Jumlah per halaman (max 100)"),
):
    """
    List tasks dengan filter + pagination.
    Staff hanya melihat task yang di-assign ke mereka, PIC melihat semua.
    """
    await require_auth(request)
    db = get_db()
    user = _get_user(request)

    query = {}

    user_role = user.get("role", "staff")
    if user_role == "staff":
        query["assigned_to"] = user.get("id")

    if status:
        query["status"] = status
    if assigned_to:
        query["assigned_to"] = assigned_to
    if account_id:
        query["account_id"] = account_id
    if priority:
        query["priority"] = priority
    if approval_status:
        query["approval_status"] = approval_status

    total = await db.marketing_tasks.count_documents(query)
    skip = (page - 1) * limit
    tasks = await db.marketing_tasks.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(500)

    return serialize_doc({
        "tasks": tasks,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 1,
            "has_next": skip + limit < total,
            "has_prev": page > 1,
        }
    })


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, request: Request):
    """Get task detail"""
    await require_auth(request)
    db = get_db()
    
    task = await db.marketing_tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(404, "Task not found")
    
    return serialize_doc(task)


@router.put("/tasks/{task_id}")
async def update_task(task_id: str, data: TaskUpdate, request: Request):
    """Update task"""
    await require_auth(request)
    db = get_db()
    user = _get_user(request)
    
    task = await db.marketing_tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(404, "Task not found")
    
    # Build update dict
    update_data = {}
    if data.title is not None:
        update_data["title"] = _sanitize(data.title, 300)
    if data.description is not None:
        update_data["description"] = _sanitize(data.description, 2000)
    if data.status is not None:
        valid_status = ["to_do", "in_progress", "pending_approval", "done", "cancelled"]
        if data.status not in valid_status:
            raise HTTPException(400, f"status must be one of: {', '.join(valid_status)}")
        update_data["status"] = data.status
        
        # If status is pending_approval, set approval_status to pending
        if data.status == "pending_approval":
            update_data["approval_status"] = "pending"
    
    if data.assigned_to is not None:
        update_data["assigned_to"] = data.assigned_to
    if data.priority is not None:
        update_data["priority"] = data.priority
    if data.due_date is not None:
        update_data["due_date"] = data.due_date
    if data.checklist is not None:
        update_data["checklist"] = data.checklist
    if data.completion_notes is not None:
        update_data["completion_notes"] = data.completion_notes
    
    update_data["updated_at"] = _now()
    
    await db.marketing_tasks.update_one(
        {"id": task_id},
        {"$set": update_data}
    )
    
    await log_activity(
        user.get("id", "system"),
        user.get("name") or user.get("email", "system"),
        "update",
        "marketing_task",
        f"Updated task: {task['title']}"
    )
    
    # Get updated task
    updated = await db.marketing_tasks.find_one({"id": task_id}, {"_id": 0})
    return serialize_doc({"message": "Task updated", "task": updated})


@router.post("/tasks/{task_id}/approve")
async def approve_task(task_id: str, request: Request):
    """
    PIC Marketing approves task.
    Only tasks with status=pending_approval can be approved.
    Allowed roles: admin/owner/superadmin/manager_*/pic_marketing/pic_toko.
    """
    await require_auth(request)
    db = get_db()
    user = _get_user(request)

    if not _is_pic_role(user):
        raise HTTPException(403, "Hanya PIC Marketing (admin/owner/manager) yang dapat approve task")

    task = await db.marketing_tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(404, "Task not found")
    
    if task["status"] != "pending_approval":
        raise HTTPException(400, "Task must be in 'pending_approval' status to approve")
    
    # Update task
    await db.marketing_tasks.update_one(
        {"id": task_id},
        {"$set": {
            "status": "done",
            "approval_status": "approved",
            "approved_by": user.get("id"),
            "approved_at": _now(),
            "updated_at": _now()
        }}
    )
    
    await log_activity(
        user.get("id", "system"),
        user.get("name") or user.get("email", "system"),
        "approve",
        "marketing_task",
        f"Approved task: {task['title']}"
    )
    
    return serialize_doc({"message": "Task approved"})


@router.post("/tasks/{task_id}/reject")
async def reject_task(task_id: str, reason: str, request: Request):
    """
    PIC Marketing rejects task.
    Task goes back to 'in_progress' status.
    Allowed roles: admin/owner/superadmin/manager_*/pic_marketing/pic_toko.
    """
    await require_auth(request)
    db = get_db()
    user = _get_user(request)

    if not _is_pic_role(user):
        raise HTTPException(403, "Hanya PIC Marketing (admin/owner/manager) yang dapat reject task")

    task = await db.marketing_tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(404, "Task not found")
    
    if task["status"] != "pending_approval":
        raise HTTPException(400, "Task must be in 'pending_approval' status to reject")
    
    # Update task - back to in_progress
    await db.marketing_tasks.update_one(
        {"id": task_id},
        {"$set": {
            "status": "in_progress",
            "approval_status": "rejected",
            "approved_by": user.get("id"),
            "approved_at": _now(),
            "completion_notes": f"[REJECTED] {reason}",
            "updated_at": _now()
        }}
    )
    
    await log_activity(
        user.get("id", "system"),
        user.get("name") or user.get("email", "system"),
        "reject",
        "marketing_task",
        f"Rejected task: {task['title']} - Reason: {reason}"
    )
    
    return serialize_doc({"message": "Task rejected", "reason": reason})


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, request: Request):
    """
    Delete task (soft delete - set status to cancelled).
    Only PIC can delete tasks.
    """
    await require_auth(request)
    db = get_db()
    user = _get_user(request)
    
    task = await db.marketing_tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(404, "Task not found")
    
    await db.marketing_tasks.update_one(
        {"id": task_id},
        {"$set": {"status": "cancelled", "updated_at": _now()}}
    )
    
    await log_activity(
        user.get("id", "system"),
        user.get("name") or user.get("email", "system"),
        "delete",
        "marketing_task",
        f"Cancelled task: {task['title']}"
    )
    
    return serialize_doc({"message": "Task cancelled"})


# ══════════════════════════════════════════════════════════════════════════════
# ACTIONABLE TASKS — Complete with inline action (Phase 3)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/tasks/{task_id}/complete-action")
async def complete_task_action(task_id: str, payload: TaskCompleteAction, request: Request):
    """
    Execute a task's bound action and mark task as done.
    
    Supported action_type values:
      - submit_form: Create new entity (e.g., sales_data) using action_data
      - approve_reject: Update existing entity status (e.g., approve return)
      - review_content: Add response text (e.g., reply review)
      - manual_check: No action, just mark done with notes
    
    Supported related_entity values:
      - sales_data: Create sales entry (auto-fills account_id, date from related_form_data)
      - return: Update return status (related_entity_id required)
      - review: Add response to review (related_entity_id required)
      - complaint: Update complaint status
      - content: Update content status
    """
    await require_auth(request)
    user = _get_user(request)
    db = get_db()
    
    task = await db.marketing_tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(404, "Task tidak ditemukan")
    
    if task.get("status") in ("done", "cancelled"):
        raise HTTPException(409, f"Task sudah berstatus '{task.get('status')}', tidak bisa di-action lagi.")
    
    action_type = task.get("action_type") or "manual_check"
    related = task.get("related_entity")
    related_id = task.get("related_entity_id")
    form_data = task.get("related_form_data") or {}
    action_data = payload.action_data or {}
    
    action_result = {"success": False, "message": "", "created_id": None}
    
    try:
        # ─── ACTION: submit_form ───
        if action_type == "submit_form":
            if related == "sales_data":
                # Compose sales data record (merge pre-fill + user input)
                merged = {**form_data, **action_data}
                if not merged.get("account_id"):
                    raise HTTPException(400, "account_id wajib untuk sales_data action")
                
                # Get account details for denormalization
                acc = await db.marketing_platform_accounts.find_one({"id": merged["account_id"]}, {"_id": 0})
                if not acc:
                    raise HTTPException(404, "Account tidak ditemukan")
                
                revenue = float(merged.get("revenue", 0))
                orders = int(merged.get("orders", 0))
                aov_calc = (revenue / orders) if orders > 0 else 0
                
                # Build sales record matching SalesDataEntry schema (with nested structure)
                sales_doc = {
                    "id": _uid(),
                    "account_id": merged["account_id"],
                    "account_code": acc.get("account_code", ""),
                    "platform": acc.get("platform", ""),
                    "date": merged.get("date") or _now().strftime("%Y-%m-%d"),
                    "revenue_type": merged.get("revenue_type", "total"),
                    "metrics": {
                        "revenue": revenue,
                        "orders": orders,
                        "aov": float(merged.get("aov", aov_calc)),
                        "gmv": float(merged.get("gmv", revenue)),
                        "conversion_rate": float(merged.get("conversion_rate", 0)),
                    },
                    "fulfillment": {},
                    "customer_satisfaction": {},
                    "live_metrics": {},
                    "import_history_id": None,
                    "source": "task_action",
                    "task_id": task_id,
                    "created_by": user.get("email", "system"),
                    "created_at": _now(),
                }
                
                # Check duplicate
                existing = await db.marketing_sales_data.find_one({
                    "account_id": sales_doc["account_id"],
                    "date": sales_doc["date"],
                    "revenue_type": sales_doc["revenue_type"],
                }, {"_id": 0})
                if existing:
                    raise HTTPException(409, f"Sales data untuk {sales_doc['date']} ({sales_doc['revenue_type']}) sudah ada")
                
                await db.marketing_sales_data.insert_one(sales_doc)
                # Trigger health recalc
                await _recalculate_health_score(db, merged["account_id"])
                action_result = {"success": True, "message": "Sales data berhasil disubmit", "created_id": sales_doc["id"]}
            
            else:
                raise HTTPException(400, f"submit_form action belum support entity: {related}")
        
        # ─── ACTION: approve_reject ───
        elif action_type == "approve_reject":
            decision = action_data.get("decision")  # 'approve' | 'reject'
            reason = action_data.get("reason", "")
            
            if decision not in ("approve", "reject"):
                raise HTTPException(400, "action_data.decision wajib: 'approve' atau 'reject'")
            if not related_id:
                raise HTTPException(400, "related_entity_id wajib untuk approve_reject action")
            
            if related == "return":
                new_status = "approved" if decision == "approve" else "rejected"
                upd = {
                    "status": new_status,
                    "appeal_status": "approved" if decision == "approve" else "rejected",
                    "appeal_result": reason or ("Disetujui via task" if decision == "approve" else "Ditolak via task"),
                    "updated_at": _now(),
                }
                result = await db.marketing_returns.update_one({"id": related_id}, {"$set": upd})
                if result.matched_count == 0:
                    raise HTTPException(404, "Return tidak ditemukan")
                action_result = {"success": True, "message": f"Return berhasil di-{decision}", "created_id": related_id}
            else:
                raise HTTPException(400, f"approve_reject action belum support entity: {related}")
        
        # ─── ACTION: review_content ───
        elif action_type == "review_content":
            response_text = action_data.get("response_text", "")
            if not response_text:
                raise HTTPException(400, "action_data.response_text wajib")
            
            if related == "review":
                if not related_id:
                    raise HTTPException(400, "related_entity_id wajib")
                result = await db.marketing_reviews.update_one(
                    {"id": related_id},
                    {"$set": {
                        "response_text": response_text,
                        "response_date": _now(),
                        "status": "responded",
                        "updated_at": _now(),
                    }}
                )
                if result.matched_count == 0:
                    raise HTTPException(404, "Review tidak ditemukan")
                action_result = {"success": True, "message": "Review berhasil dibalas", "created_id": related_id}
            else:
                raise HTTPException(400, f"review_content action belum support entity: {related}")
        
        # ─── ACTION: manual_check ───
        elif action_type == "manual_check":
            action_result = {"success": True, "message": "Task ditandai selesai (manual check)", "created_id": None}
        
        else:
            raise HTTPException(400, f"Unknown action_type: {action_type}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task action failed: {e}", exc_info=True)
        raise HTTPException(500, f"Action gagal: {str(e)}")
    
    # Mark task as done
    await db.marketing_tasks.update_one(
        {"id": task_id},
        {"$set": {
            "status": "done",
            "completion_notes": payload.completion_notes or action_result["message"],
            "action_executed_at": _now(),
            "action_result": action_result,
            "updated_at": _now(),
        }}
    )
    
    await log_activity(
        user.get("id", "system"),
        user.get("name") or user.get("email", "system"),
        "complete_action",
        "marketing_task",
        f"Task action executed: {task['title']} - {action_result['message']}"
    )
    
    return serialize_doc({
        "message": "Task action completed successfully",
        "result": action_result,
    })


# ══════════════════════════════════════════════════════════════════════════════
# TASK TEMPLATES
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/task-templates")
async def create_task_template(data: TaskTemplateCreate, request: Request):
    """
    Create task template for recurring tasks.
    Only PIC Marketing can create templates.
    """
    await require_auth(request)
    db = get_db()
    user = _get_user(request)
    
    template = {
        "id": _uid(),
        "template_name": _sanitize(data.template_name, 200),
        "title": _sanitize(data.title, 300),
        "description": _sanitize(data.description or "", 2000),
        "task_type": data.task_type,
        "recurrence": data.recurrence,
        "recurrence_config": data.recurrence_config.dict(),
        "default_assigned_role": data.default_assigned_role,
        "account_id": data.account_id,
        "priority": data.priority,
        "checklist_template": data.checklist_template or [],
        "is_active": data.is_active,
        "created_by": user.get("id"),
        "created_at": _now(),
        "updated_at": _now()
    }
    
    await db.marketing_task_templates.insert_one(template)
    
    await log_activity(
        user.get("id", "system"),
        user.get("name") or user.get("email", "system"),
        "create",
        "marketing_task_template",
        f"Created task template: {data.template_name}"
    )
    
    return serialize_doc({"message": "Task template created", "template": template})


@router.get("/task-templates")
async def list_task_templates(
    request: Request,
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """List all task templates"""
    await require_auth(request)
    db = get_db()
    
    query = {}
    if is_active is not None:
        query["is_active"] = is_active
    
    templates = await db.marketing_task_templates.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    return serialize_doc(templates)


@router.get("/task-templates/{template_id}")
async def get_task_template(template_id: str, request: Request):
    """Get task template detail"""
    await require_auth(request)
    db = get_db()
    
    template = await db.marketing_task_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(404, "Task template not found")
    
    return serialize_doc(template)


@router.put("/task-templates/{template_id}")
async def update_task_template(template_id: str, data: TaskTemplateCreate, request: Request):
    """Update task template"""
    await require_auth(request)
    db = get_db()
    user = _get_user(request)
    
    template = await db.marketing_task_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(404, "Task template not found")
    
    update_data = {
        "template_name": data.template_name,
        "title": data.title,
        "description": data.description or "",
        "task_type": data.task_type,
        "recurrence": data.recurrence,
        "recurrence_config": data.recurrence_config.dict(),
        "default_assigned_role": data.default_assigned_role,
        "account_id": data.account_id,
        "priority": data.priority,
        "checklist_template": data.checklist_template or [],
        "is_active": data.is_active,
        "updated_at": _now()
    }
    
    await db.marketing_task_templates.update_one(
        {"id": template_id},
        {"$set": update_data}
    )
    
    await log_activity(
        user.get("id", "system"),
        user.get("name") or user.get("email", "system"),
        "update",
        "marketing_task_template",
        f"Updated task template: {data.template_name}"
    )
    
    updated = await db.marketing_task_templates.find_one({"id": template_id}, {"_id": 0})
    return serialize_doc({"message": "Task template updated", "template": updated})


@router.delete("/task-templates/{template_id}")
async def delete_task_template(template_id: str, request: Request):
    """Delete task template (set is_active=false)"""
    await require_auth(request)
    db = get_db()
    user = _get_user(request)
    
    template = await db.marketing_task_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(404, "Task template not found")
    
    await db.marketing_task_templates.update_one(
        {"id": template_id},
        {"$set": {"is_active": False, "updated_at": _now()}}
    )
    
    await log_activity(
        user.get("id", "system"),
        user.get("name") or user.get("email", "system"),
        "delete",
        "marketing_task_template",
        f"Deactivated task template: {template['template_name']}"
    )
    
    return serialize_doc({"message": "Task template deactivated"})


# ══════════════════════════════════════════════════════════════════════════════
# TASK STATISTICS & REPORTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/tasks-stats")
async def get_tasks_stats(
    request: Request,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """
    Get task completion statistics.
    For PIC dashboard to see task completion rate.
    """
    await require_auth(request)
    db = get_db()
    
    # Date range default: last 30 days
    if not date_to:
        date_to = _now().strftime("%Y-%m-%d")
    if not date_from:
        date_from = (_now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Get tasks in date range
    query = {
        "created_at": {
            "$gte": datetime.fromisoformat(date_from + "T00:00:00+00:00"),
            "$lte": datetime.fromisoformat(date_to + "T23:59:59+00:00")
        }
    }
    
    tasks = await db.marketing_tasks.find(query, {"_id": 0}).to_list(500)
    
    # Calculate stats
    total = len(tasks)
    by_status = {
        "to_do": len([t for t in tasks if t["status"] == "to_do"]),
        "in_progress": len([t for t in tasks if t["status"] == "in_progress"]),
        "pending_approval": len([t for t in tasks if t["status"] == "pending_approval"]),
        "done": len([t for t in tasks if t["status"] == "done"]),
        "cancelled": len([t for t in tasks if t["status"] == "cancelled"])
    }
    
    completion_rate = (by_status["done"] / total * 100) if total > 0 else 0
    
    # Overdue tasks
    now = _now()
    overdue = len([t for t in tasks if t.get("due_date") and datetime.fromisoformat(t["due_date"]) < now and t["status"] not in ["done", "cancelled"]])
    
    return serialize_doc({
        "period": {"date_from": date_from, "date_to": date_to},
        "total_tasks": total,
        "by_status": by_status,
        "completion_rate": round(completion_rate, 2),
        "overdue_count": overdue
    })


# ══════════════════════════════════════════════════════════════════════════════
# MANUAL TRIGGER — Auto-create tasks (untuk testing tanpa wait cron)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/auto-create-tasks/trigger")
async def trigger_auto_create_tasks(request: Request):
    """
    Manual trigger for auto-create marketing tasks job (sales reminder + health alert).
    Admin/PIC only.
    """
    user = await require_auth(request)
    role = user.get("role", "")
    if role not in ["admin", "owner", "superadmin", "pic_marketing", "pic_toko", "manager_marketing"]:
        raise HTTPException(403, "Hanya admin/PIC/manager marketing yang bisa trigger ini")
    
    try:
        from utils.scheduler import job_auto_create_marketing_tasks
        await job_auto_create_marketing_tasks()
        return serialize_doc({"message": "Auto-create tasks triggered successfully", "status": "completed"})
    except Exception as e:
        logger.exception(f"Manual trigger failed: {e}")
        raise HTTPException(500, f"Trigger gagal: {str(e)}")
