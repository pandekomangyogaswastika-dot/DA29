"""
CV. Dewi Aditya — Marketing Portal Phase 5: KOL & Creator Management

Collections:
- marketing_kol_creators: Creator profiles & login credentials
- marketing_creator_sessions: Live session performance data
- marketing_creator_item_requests: Creator requests for promo items
- marketing_creator_catalog: Product catalog per account (linked to FG inventory)

Auth:
- Creator portal uses separate JWT with audience='creator-portal'
- Internal admin uses standard app JWT via require_auth

Author: CV. Dewi Aditya Development Team
Date: 2026-05-02
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field
from database import get_db
from auth import JWT_SECRET, hash_password, verify_password, require_auth, serialize_doc, log_activity
import jwt as pyjwt

router = APIRouter(prefix='/api/marketing', tags=['Marketing-KOL'])

CREATOR_TOKEN_AUDIENCE = 'creator-portal'
CREATOR_TOKEN_HOURS = 24


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def _uid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


def _get_user(request: Request) -> dict:
    return getattr(request.state, 'user', {"id": "system", "email": "system", "role": "admin"})


# ──────────────────────────────────────────────────────────────
# CREATOR PORTAL JWT
# ──────────────────────────────────────────────────────────────

def _create_creator_token(creator: dict) -> str:
    payload = {
        'sub': creator['id'],
        'email': creator['login_email'],
        'creator_id': creator['id'],
        'creator_name': creator.get('name', ''),
        'creator_code': creator.get('creator_code', ''),
        'aud': CREATOR_TOKEN_AUDIENCE,
        'exp': _now() + timedelta(hours=CREATOR_TOKEN_HOURS),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm='HS256')


def _decode_creator_token(token: str) -> Optional[dict]:
    try:
        return pyjwt.decode(
            token, JWT_SECRET, algorithms=['HS256'], audience=CREATOR_TOKEN_AUDIENCE
        )
    except Exception:
        return None


async def require_creator_auth(request: Request) -> dict:
    """Require creator portal authentication."""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        raise HTTPException(401, 'Token tidak ditemukan')
    token = auth.split(' ', 1)[1]
    payload = _decode_creator_token(token)
    if not payload:
        raise HTTPException(401, 'Token tidak valid atau kadaluarsa')
    db = get_db()
    creator = await db.marketing_kol_creators.find_one({'id': payload.get('creator_id')}, {'_id': 0})
    if not creator or creator.get('status') != 'active':
        raise HTTPException(403, 'Akun creator tidak aktif')
    creator.pop('login_password_hash', None)
    return creator


# ──────────────────────────────────────────────────────────────
# BRUTE-FORCE PROTECTION (Creator Portal login)
# ──────────────────────────────────────────────────────────────
# Track failed login attempts in MongoDB collection `marketing_kol_login_attempts`.
# Identifier = "{ip}:{email}". 5 failed attempts → 15 min lockout. Cleared on success.

CREATOR_LOGIN_MAX_ATTEMPTS = 5
CREATOR_LOGIN_LOCKOUT_MINUTES = 15


def _client_ip(request: Request) -> str:
    fwd = request.headers.get('X-Forwarded-For')
    if fwd:
        return fwd.split(',')[0].strip()
    return getattr(request.client, 'host', 'unknown') if request.client else 'unknown'


async def _check_creator_lockout(db, identifier: str) -> None:
    """Raise 429 if identifier is locked out. Auto-clear if lockout expired."""
    doc = await db.marketing_kol_login_attempts.find_one({'identifier': identifier}, {'_id': 0})
    if not doc:
        return
    locked_until = doc.get('locked_until')
    if locked_until is None:
        return
    # MongoDB may return naive datetime — normalize to UTC-aware
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    now = _now()
    if locked_until > now:
        remaining = int((locked_until - now).total_seconds() / 60) + 1
        raise HTTPException(
            429,
            f'Terlalu banyak percobaan login. Coba lagi dalam {remaining} menit.'
        )
    # Lockout expired → reset
    await db.marketing_kol_login_attempts.delete_one({'identifier': identifier})


async def _record_failed_attempt(db, identifier: str) -> int:
    """Increment failed attempts. Lock account after MAX. Returns remaining attempts."""
    doc = await db.marketing_kol_login_attempts.find_one_and_update(
        {'identifier': identifier},
        {
            '$inc': {'attempts': 1},
            '$set': {'last_attempt_at': _now()},
            '$setOnInsert': {'identifier': identifier, 'first_attempt_at': _now()},
        },
        upsert=True,
        return_document=True,
    )
    attempts = (doc or {}).get('attempts', 1)
    if attempts >= CREATOR_LOGIN_MAX_ATTEMPTS:
        locked_until = _now() + timedelta(minutes=CREATOR_LOGIN_LOCKOUT_MINUTES)
        await db.marketing_kol_login_attempts.update_one(
            {'identifier': identifier},
            {'$set': {'locked_until': locked_until}},
        )
    return max(0, CREATOR_LOGIN_MAX_ATTEMPTS - attempts)


async def _clear_attempts(db, identifier: str) -> None:
    await db.marketing_kol_login_attempts.delete_one({'identifier': identifier})



# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════════════════

class CreatorCreate(BaseModel):
    name: str = Field(..., min_length=1)
    creator_code: str = Field(..., description="Unique code e.g. KOL-001")
    login_email: str = Field(..., description="Creator login email")
    login_password: str = Field(..., min_length=6, description="Creator login password")
    phone: Optional[str] = None
    platforms: Optional[dict] = Field(default_factory=dict, description="{'shopee': 'handle', 'tiktok': 'handle'}")
    assigned_account_ids: Optional[List[str]] = Field(default_factory=list, description="Account IDs this creator is assigned to")
    kpi_targets: Optional[dict] = Field(default_factory=dict, description="{'monthly_revenue': 10000000, 'monthly_sessions': 8, 'monthly_viewers': 50000}")
    notes: Optional[str] = None


class CreatorUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    platforms: Optional[dict] = None
    assigned_account_ids: Optional[List[str]] = None
    kpi_targets: Optional[dict] = None
    notes: Optional[str] = None
    status: Optional[str] = Field(None, description="active | inactive")
    login_password: Optional[str] = Field(None, min_length=6, description="New password (optional)")


class SessionCreate(BaseModel):
    creator_id: str
    account_id: str
    date: str = Field(..., description="YYYY-MM-DD")
    platform: str = Field(..., description="shopee | tiktokshop | tokopedia")
    session_name: Optional[str] = Field(None, description="e.g. Live Session Siang")
    duration_minutes: int = Field(0, ge=0)
    viewers: int = Field(0, ge=0)
    peak_viewers: int = Field(0, ge=0)
    revenue: float = Field(0, ge=0)
    orders: int = Field(0, ge=0)
    items_promoted: Optional[List[str]] = Field(default_factory=list, description="List of product names promoted")
    notes: Optional[str] = None


class ItemRequestCreate(BaseModel):
    account_id: str
    catalog_item_id: str
    quantity_requested: int = Field(..., ge=1)
    purpose: Optional[str] = Field(None, description="Tujuan promo: flash sale, review, giveaway, dll")
    notes: Optional[str] = None


class CatalogItemCreate(BaseModel):
    account_id: str
    fg_product_id: str = Field(..., description="Material ID from rahaza_materials (type=fg)")
    product_name: str
    sku: str
    category: Optional[str] = None
    unit_price: float = Field(0, ge=0)
    description: Optional[str] = None
    is_active: bool = True


class CreatorLoginIn(BaseModel):
    email: str
    password: str


# ══════════════════════════════════════════════════════════════════════════════
# CREATOR PORTAL AUTH
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/creator-portal/auth/login')
async def creator_login(payload: CreatorLoginIn, request: Request):
    """Creator portal login — returns JWT with audience='creator-portal'.

    Brute-force protected: 5 failed attempts per IP+email → 15 min lockout.
    """
    db = get_db()
    email = payload.email.lower().strip()
    identifier = f"{_client_ip(request)}:{email}"

    # 1. Check lockout BEFORE any DB read on creator
    await _check_creator_lockout(db, identifier)

    creator = await db.marketing_kol_creators.find_one(
        {'login_email': email}, {'_id': 0}
    )
    if not creator:
        remaining = await _record_failed_attempt(db, identifier)
        raise HTTPException(
            401,
            f'Email atau password salah. Sisa {remaining} percobaan.'
            if remaining > 0
            else 'Akun terkunci sementara karena terlalu banyak percobaan login.'
        )
    if not verify_password(payload.password, creator.get('login_password_hash', '')):
        remaining = await _record_failed_attempt(db, identifier)
        raise HTTPException(
            401,
            f'Email atau password salah. Sisa {remaining} percobaan.'
            if remaining > 0
            else 'Akun terkunci sementara karena terlalu banyak percobaan login.'
        )
    if creator.get('status') != 'active':
        raise HTTPException(403, 'Akun creator tidak aktif. Hubungi admin.')

    # Success → clear any failed attempts
    await _clear_attempts(db, identifier)

    # Update last login
    await db.marketing_kol_creators.update_one(
        {'id': creator['id']},
        {'$set': {'last_login_at': _now()}}
    )

    token = _create_creator_token(creator)
    return {
        'token': token,
        'creator_id': creator['id'],
        'creator_name': creator['name'],
        'creator_code': creator['creator_code'],
        'assigned_account_ids': creator.get('assigned_account_ids', []),
    }


@router.get('/creator-portal/auth/profile')
async def creator_get_profile(request: Request):
    """Get creator profile (creator portal auth)"""
    creator = await require_creator_auth(request)
    db = get_db()

    # Get assigned accounts
    assigned = await db.marketing_platform_accounts.find(
        {'id': {'$in': creator.get('assigned_account_ids', [])}}, {'_id': 0}
    ).to_list(500)

    return serialize_doc({
        **creator,
        'assigned_accounts': assigned
    })


# ══════════════════════════════════════════════════════════════════════════════
# CREATOR PORTAL — CATALOG & REQUESTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/creator-portal/catalog')
async def creator_get_catalog(
    request: Request,
    account_id: Optional[str] = Query(None),
):
    """
    Get product catalog for creator — shows items available to promote.
    Includes real-time stock from FG inventory.
    """
    creator = await require_creator_auth(request)
    db = get_db()

    # Only show catalog for accounts this creator is assigned to
    allowed_account_ids = creator.get('assigned_account_ids', [])

    query = {'is_active': True}
    if account_id:
        if account_id not in allowed_account_ids:
            raise HTTPException(403, 'Creator tidak memiliki akses ke akun ini')
        query['account_id'] = account_id
    elif allowed_account_ids:
        query['account_id'] = {'$in': allowed_account_ids}
    else:
        return []

    catalog = await db.marketing_creator_catalog.find(query, {'_id': 0}).sort('product_name', 1).to_list(500)

    # Enrich with real-time FG stock
    for item in catalog:
        fg_id = item.get('fg_product_id')
        if fg_id:
            # Get default location
            default_loc = await db.rahaza_locations.find_one({'active': True}, {'_id': 0})
            loc_id = default_loc['id'] if default_loc else None
            stock_doc = await db.rahaza_material_stock.find_one(
                {'material_id': fg_id, 'location_id': loc_id}, {'_id': 0}
            )
            item['stock_qty'] = float(stock_doc.get('qty', 0)) if stock_doc else 0
        else:
            item['stock_qty'] = 0

    return serialize_doc(catalog)


@router.post('/creator-portal/requests')
async def creator_request_item(data: ItemRequestCreate, request: Request):
    """Creator requests an item from catalog for live promotion"""
    creator = await require_creator_auth(request)
    db = get_db()

    # Validate account access
    allowed = creator.get('assigned_account_ids', [])
    if data.account_id not in allowed:
        raise HTTPException(403, 'Creator tidak memiliki akses ke akun ini')

    # Validate catalog item
    catalog_item = await db.marketing_creator_catalog.find_one(
        {'id': data.catalog_item_id, 'is_active': True}, {'_id': 0}
    )
    if not catalog_item:
        raise HTTPException(404, 'Produk tidak ditemukan di katalog')

    # Check FG stock availability
    fg_id = catalog_item.get('fg_product_id')
    stock_qty = 0
    if fg_id:
        default_loc = await db.rahaza_locations.find_one({'active': True}, {'_id': 0})
        loc_id = default_loc['id'] if default_loc else None
        stock_doc = await db.rahaza_material_stock.find_one(
            {'material_id': fg_id, 'location_id': loc_id}, {'_id': 0}
        )
        stock_qty = float(stock_doc.get('qty', 0)) if stock_doc else 0

    req = {
        'id': _uid(),
        'creator_id': creator['id'],
        'creator_name': creator['name'],
        'creator_code': creator['creator_code'],
        'account_id': data.account_id,
        'catalog_item_id': data.catalog_item_id,
        'product_name': catalog_item['product_name'],
        'sku': catalog_item['sku'],
        'fg_product_id': fg_id,
        'quantity_requested': data.quantity_requested,
        'stock_at_request': stock_qty,
        'purpose': data.purpose or '',
        'notes': data.notes or '',
        'status': 'pending',
        'reviewed_at': None,
        'reviewed_by': None,
        'rejection_reason': None,
        'created_at': _now(),
    }

    await db.marketing_creator_item_requests.insert_one(req)
    return serialize_doc({'message': 'Permintaan berhasil dikirim', 'request': req})


@router.get('/creator-portal/my-requests')
async def creator_my_requests(request: Request):
    """Get creator's own item requests"""
    creator = await require_creator_auth(request)
    db = get_db()

    requests = await db.marketing_creator_item_requests.find(
        {'creator_id': creator['id']}, {'_id': 0}
    ).sort('created_at', -1).to_list(500)

    return serialize_doc(requests)


@router.get('/creator-portal/my-performance')
async def creator_my_performance(
    request: Request,
    month: Optional[str] = Query(None, description="YYYY-MM, defaults to current month"),
):
    """Get creator's own live session performance"""
    creator = await require_creator_auth(request)
    db = get_db()

    if not month:
        month = _now().strftime('%Y-%m')

    # Query sessions in this month
    date_from = f'{month}-01'
    # Get last day of month
    year, mon = int(month.split('-')[0]), int(month.split('-')[1])
    next_month = datetime(year, mon, 1, tzinfo=timezone.utc) + timedelta(days=32)
    date_to = (next_month.replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d')

    sessions = await db.marketing_creator_sessions.find(
        {'creator_id': creator['id'], 'date': {'$gte': date_from, '$lte': date_to}},
        {'_id': 0}
    ).sort('date', -1).to_list(500)

    # KPI targets
    kpi = creator.get('kpi_targets', {})
    total_revenue = sum(s.get('revenue', 0) for s in sessions)
    total_sessions = len(sessions)
    total_viewers = sum(s.get('viewers', 0) for s in sessions)

    return serialize_doc({
        'month': month,
        'sessions': sessions,
        'summary': {
            'total_sessions': total_sessions,
            'total_revenue': round(total_revenue),
            'total_viewers': total_viewers,
            'total_orders': sum(s.get('orders', 0) for s in sessions),
        },
        'kpi_targets': kpi,
        'kpi_progress': {
            'revenue_pct': round(total_revenue / kpi['monthly_revenue'] * 100, 1) if kpi.get('monthly_revenue') else None,
            'sessions_pct': round(total_sessions / kpi['monthly_sessions'] * 100, 1) if kpi.get('monthly_sessions') else None,
            'viewers_pct': round(total_viewers / kpi['monthly_viewers'] * 100, 1) if kpi.get('monthly_viewers') else None,
        }
    })


@router.get('/creator-portal/my-kpi')
async def creator_my_kpi(request: Request):
    """Get creator's KPI summary — current month vs target"""
    creator = await require_creator_auth(request)
    db = get_db()

    month = _now().strftime('%Y-%m')
    date_from = f'{month}-01'
    year, mon = int(month.split('-')[0]), int(month.split('-')[1])
    next_month = datetime(year, mon, 1, tzinfo=timezone.utc) + timedelta(days=32)
    date_to = (next_month.replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d')

    sessions = await db.marketing_creator_sessions.find(
        {'creator_id': creator['id'], 'date': {'$gte': date_from, '$lte': date_to}},
        {'_id': 0}
    ).to_list(500)

    kpi = creator.get('kpi_targets', {})
    total_revenue = sum(s.get('revenue', 0) for s in sessions)
    total_sessions = len(sessions)
    total_viewers = sum(s.get('viewers', 0) for s in sessions)

    return serialize_doc({
        'month': month,
        'creator_name': creator['name'],
        'kpi_targets': kpi,
        'actuals': {
            'monthly_revenue': round(total_revenue),
            'monthly_sessions': total_sessions,
            'monthly_viewers': total_viewers,
        },
        'progress': {
            'revenue_pct': round(total_revenue / kpi['monthly_revenue'] * 100, 1) if kpi.get('monthly_revenue') else None,
            'sessions_pct': round(total_sessions / kpi['monthly_sessions'] * 100, 1) if kpi.get('monthly_sessions') else None,
            'viewers_pct': round(total_viewers / kpi['monthly_viewers'] * 100, 1) if kpi.get('monthly_viewers') else None,
        }
    })


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — CREATOR CRUD
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/kol/creators')
async def create_creator(data: CreatorCreate, request: Request):
    """Admin creates a new KOL creator account"""
    await require_auth(request)
    db = get_db()

    # Check duplicate email / code
    if await db.marketing_kol_creators.find_one({'login_email': data.login_email.lower().strip()}):
        raise HTTPException(400, f"Email '{data.login_email}' sudah terdaftar")
    if await db.marketing_kol_creators.find_one({'creator_code': data.creator_code}):
        raise HTTPException(400, f"Kode creator '{data.creator_code}' sudah ada")

    creator = {
        'id': _uid(),
        'creator_code': data.creator_code,
        'name': data.name,
        'login_email': data.login_email.lower().strip(),
        'login_password_hash': hash_password(data.login_password),
        'phone': data.phone or '',
        'platforms': data.platforms or {},
        'assigned_account_ids': data.assigned_account_ids or [],
        'kpi_targets': data.kpi_targets or {
            'monthly_revenue': 0,
            'monthly_sessions': 0,
            'monthly_viewers': 0,
        },
        'notes': data.notes or '',
        'status': 'active',
        'last_login_at': None,
        'created_at': _now(),
        'created_by': _get_user(request).get('email', 'system'),
        'updated_at': _now(),
    }

    await db.marketing_kol_creators.insert_one(creator)
    creator.pop('login_password_hash', None)

    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'create', 'marketing_kol_creator',
        f"Created creator: {data.name} ({data.creator_code})"
    )

    return serialize_doc({'message': 'Creator berhasil dibuat', 'creator': creator})


@router.get('/kol/creators')
async def list_creators(
    request: Request,
    status: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None, description="Filter by assigned account"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Admin lists all KOL creators dengan pagination"""
    await require_auth(request)
    db = get_db()

    query = {}
    if status:
        query['status'] = status
    if account_id:
        query['assigned_account_ids'] = account_id

    total = await db.marketing_kol_creators.count_documents(query)
    skip = (page - 1) * limit
    creators = await db.marketing_kol_creators.find(
        query, {'_id': 0, 'login_password_hash': 0}
    ).sort('created_at', -1).skip(skip).limit(limit).to_list(500)

    # Enrich with current month performance
    month = _now().strftime('%Y-%m')
    date_from = f'{month}-01'
    year, mon = int(month.split('-')[0]), int(month.split('-')[1])
    next_month = datetime(year, mon, 1, tzinfo=timezone.utc) + timedelta(days=32)
    date_to = (next_month.replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d')

    # Batch fetch sessions untuk semua creators (fix N+1)
    creator_ids = [c['id'] for c in creators]
    all_sessions = await db.marketing_creator_sessions.find(
        {'creator_id': {'$in': creator_ids}, 'date': {'$gte': date_from, '$lte': date_to}},
        {'_id': 0, 'creator_id': 1, 'revenue': 1, 'viewers': 1}
    ).to_list(500)

    from collections import defaultdict as _dd
    sessions_by_creator = _dd(list)
    for s in all_sessions:
        sessions_by_creator[s['creator_id']].append(s)

    for c in creators:
        sessions = sessions_by_creator.get(c['id'], [])
        c['this_month'] = {
            'sessions': len(sessions),
            'revenue': round(sum(s.get('revenue', 0) for s in sessions)),
            'viewers': sum(s.get('viewers', 0) for s in sessions),
        }

    return serialize_doc({
        'creators': creators,
        'pagination': {
            'total': total, 'page': page, 'limit': limit,
            'total_pages': (total + limit - 1) // limit if total > 0 else 1,
            'has_next': skip + limit < total, 'has_prev': page > 1,
        }
    })


@router.get('/kol/creators/{creator_id}')
async def get_creator(creator_id: str, request: Request):
    """Get creator detail"""
    await require_auth(request)
    db = get_db()

    creator = await db.marketing_kol_creators.find_one({'id': creator_id}, {'_id': 0, 'login_password_hash': 0})
    if not creator:
        raise HTTPException(404, 'Creator tidak ditemukan')

    # Get assigned accounts
    assigned = await db.marketing_platform_accounts.find(
        {'id': {'$in': creator.get('assigned_account_ids', [])}}, {'_id': 0}
    ).to_list(500)
    creator['assigned_accounts'] = assigned

    return serialize_doc(creator)


@router.put('/kol/creators/{creator_id}')
async def update_creator(creator_id: str, data: CreatorUpdate, request: Request):
    """Admin updates a creator"""
    await require_auth(request)
    db = get_db()

    creator = await db.marketing_kol_creators.find_one({'id': creator_id}, {'_id': 0})
    if not creator:
        raise HTTPException(404, 'Creator tidak ditemukan')

    update_data = {}
    if data.name is not None: update_data['name'] = data.name
    if data.phone is not None: update_data['phone'] = data.phone
    if data.platforms is not None: update_data['platforms'] = data.platforms
    if data.assigned_account_ids is not None: update_data['assigned_account_ids'] = data.assigned_account_ids
    if data.kpi_targets is not None: update_data['kpi_targets'] = data.kpi_targets
    if data.notes is not None: update_data['notes'] = data.notes
    if data.status is not None:
        if data.status not in ('active', 'inactive'):
            raise HTTPException(400, 'status harus active atau inactive')
        update_data['status'] = data.status
    if data.login_password:
        update_data['login_password_hash'] = hash_password(data.login_password)

    update_data['updated_at'] = _now()
    await db.marketing_kol_creators.update_one({'id': creator_id}, {'$set': update_data})

    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'update', 'marketing_kol_creator',
        f"Updated creator: {creator['name']}"
    )

    updated = await db.marketing_kol_creators.find_one({'id': creator_id}, {'_id': 0, 'login_password_hash': 0})
    return serialize_doc({'message': 'Creator berhasil diupdate', 'creator': updated})


@router.delete('/kol/creators/{creator_id}')
async def deactivate_creator(creator_id: str, request: Request):
    """Admin deactivates (soft delete) a creator"""
    await require_auth(request)
    db = get_db()

    creator = await db.marketing_kol_creators.find_one({'id': creator_id}, {'_id': 0})
    if not creator:
        raise HTTPException(404, 'Creator tidak ditemukan')

    await db.marketing_kol_creators.update_one(
        {'id': creator_id},
        {'$set': {'status': 'inactive', 'updated_at': _now()}}
    )

    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'deactivate', 'marketing_kol_creator',
        f"Deactivated creator: {creator['name']}"
    )

    return serialize_doc({'message': 'Creator dinonaktifkan'})


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — LIVE SESSIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/kol/sessions')
async def create_session(data: SessionCreate, request: Request):
    """Admin/creator logs a live session"""
    await require_auth(request)
    db = get_db()

    creator = await db.marketing_kol_creators.find_one({'id': data.creator_id}, {'_id': 0})
    if not creator:
        raise HTTPException(404, 'Creator tidak ditemukan')

    account = await db.marketing_platform_accounts.find_one({'id': data.account_id}, {'_id': 0})
    if not account:
        raise HTTPException(404, 'Account tidak ditemukan')

    session = {
        'id': _uid(),
        'creator_id': data.creator_id,
        'creator_name': creator['name'],
        'creator_code': creator['creator_code'],
        'account_id': data.account_id,
        'account_name': account['account_name'],
        'platform': data.platform,
        'date': data.date,
        'session_name': data.session_name or f"Live {data.date}",
        'duration_minutes': data.duration_minutes,
        'viewers': data.viewers,
        'peak_viewers': data.peak_viewers,
        'revenue': data.revenue,
        'orders': data.orders,
        'items_promoted': data.items_promoted or [],
        'notes': data.notes or '',
        'created_at': _now(),
        'created_by': _get_user(request).get('email', 'system'),
    }

    await db.marketing_creator_sessions.insert_one(session)

    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'create', 'marketing_creator_session',
        f"Logged session for {creator['name']}: {data.date} - Rp{data.revenue:,.0f}"
    )

    return serialize_doc({'message': 'Sesi berhasil dicatat', 'session': session})


@router.get('/kol/sessions')
async def list_sessions(
    request: Request,
    creator_id: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Admin lists all live sessions"""
    await require_auth(request)
    db = get_db()

    query = {}
    if creator_id:
        query['creator_id'] = creator_id
    if account_id:
        query['account_id'] = account_id
    if date_from or date_to:
        query['date'] = {}
        if date_from: query['date']['$gte'] = date_from
        if date_to: query['date']['$lte'] = date_to

    sessions = await db.marketing_creator_sessions.find(query, {'_id': 0}).sort('date', -1).to_list(500)
    return serialize_doc(sessions)


@router.delete('/kol/sessions/{session_id}')
async def delete_session(session_id: str, request: Request):
    """Admin deletes a session"""
    await require_auth(request)
    db = get_db()
    sess = await db.marketing_creator_sessions.find_one({'id': session_id}, {'_id': 0})
    if not sess:
        raise HTTPException(404, 'Sesi tidak ditemukan')
    await db.marketing_creator_sessions.delete_one({'id': session_id})
    return serialize_doc({'message': 'Sesi dihapus'})


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — ITEM REQUESTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/kol/requests')
async def list_requests(
    request: Request,
    status: Optional[str] = Query(None, description="pending | approved | rejected"),
    creator_id: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Admin lists all item requests dari creators, dengan pagination"""
    await require_auth(request)
    db = get_db()

    query = {}
    if status: query['status'] = status
    if creator_id: query['creator_id'] = creator_id
    if account_id: query['account_id'] = account_id

    total = await db.marketing_creator_item_requests.count_documents(query)
    skip = (page - 1) * limit
    requests = await db.marketing_creator_item_requests.find(
        query, {'_id': 0}
    ).sort('created_at', -1).skip(skip).limit(limit).to_list(500)

    # Batch enrich dengan real-time stock
    fg_ids = list(set(r.get('fg_product_id') for r in requests if r.get('fg_product_id')))
    if fg_ids:
        default_loc = await db.rahaza_locations.find_one({'active': True}, {'_id': 0})
        loc_id = default_loc['id'] if default_loc else None
        stocks = await db.rahaza_material_stock.find(
            {'material_id': {'$in': fg_ids}, 'location_id': loc_id}, {'_id': 0}
        ).to_list(500)
        stock_map = {s['material_id']: float(s.get('qty', 0)) for s in stocks}
        for req in requests:
            req['current_stock'] = stock_map.get(req.get('fg_product_id'), 0)
    else:
        for req in requests:
            req['current_stock'] = 0

    return serialize_doc({
        'requests': requests,
        'pagination': {
            'total': total, 'page': page, 'limit': limit,
            'total_pages': (total + limit - 1) // limit if total > 0 else 1,
            'has_next': skip + limit < total, 'has_prev': page > 1,
        }
    })


@router.post('/kol/requests/{request_id}/approve')
async def approve_request(request_id: str, request: Request):
    """Admin approves a creator item request"""
    await require_auth(request)
    db = get_db()

    req = await db.marketing_creator_item_requests.find_one({'id': request_id}, {'_id': 0})
    if not req:
        raise HTTPException(404, 'Request tidak ditemukan')
    if req['status'] != 'pending':
        raise HTTPException(400, f"Request sudah {req['status']}")

    user = _get_user(request)
    await db.marketing_creator_item_requests.update_one(
        {'id': request_id},
        {'$set': {
            'status': 'approved',
            'reviewed_at': _now(),
            'reviewed_by': user.get('email', 'admin'),
        }}
    )

    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'approve', 'marketing_creator_request',
        f"Approved request {request_id} from {req['creator_name']} for {req['product_name']}"
    )

    return serialize_doc({'message': 'Request disetujui'})


@router.post('/kol/requests/{request_id}/reject')
async def reject_request(request_id: str, reason: str, request: Request):
    """Admin rejects a creator item request"""
    await require_auth(request)
    db = get_db()

    req = await db.marketing_creator_item_requests.find_one({'id': request_id}, {'_id': 0})
    if not req:
        raise HTTPException(404, 'Request tidak ditemukan')
    if req['status'] != 'pending':
        raise HTTPException(400, f"Request sudah {req['status']}")

    user = _get_user(request)
    await db.marketing_creator_item_requests.update_one(
        {'id': request_id},
        {'$set': {
            'status': 'rejected',
            'reviewed_at': _now(),
            'reviewed_by': user.get('email', 'admin'),
            'rejection_reason': reason,
        }}
    )

    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'reject', 'marketing_creator_request',
        f"Rejected request {request_id}: {reason}"
    )

    return serialize_doc({'message': 'Request ditolak', 'reason': reason})


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — CATALOG MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/kol/catalog')
async def list_catalog(
    request: Request,
    account_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
):
    """Admin lists all catalog items with FG stock"""
    await require_auth(request)
    db = get_db()

    query = {}
    if account_id: query['account_id'] = account_id
    if is_active is not None: query['is_active'] = is_active

    items = await db.marketing_creator_catalog.find(query, {'_id': 0}).sort('product_name', 1).to_list(500)

    # Enrich with real-time FG stock
    for item in items:
        fg_id = item.get('fg_product_id')
        if fg_id:
            default_loc = await db.rahaza_locations.find_one({'active': True}, {'_id': 0})
            loc_id = default_loc['id'] if default_loc else None
            stock_doc = await db.rahaza_material_stock.find_one(
                {'material_id': fg_id, 'location_id': loc_id}, {'_id': 0}
            )
            item['stock_qty'] = float(stock_doc.get('qty', 0)) if stock_doc else 0
        else:
            item['stock_qty'] = 0

    return serialize_doc(items)


@router.post('/kol/catalog')
async def add_catalog_item(data: CatalogItemCreate, request: Request):
    """Admin adds a product to the creator catalog"""
    await require_auth(request)
    db = get_db()

    # Validate account
    account = await db.marketing_platform_accounts.find_one({'id': data.account_id}, {'_id': 0})
    if not account:
        raise HTTPException(404, 'Account tidak ditemukan')

    # Validate FG product (optional — product may not yet be in FG system)
    if data.fg_product_id:
        await db.rahaza_materials.find_one({'id': data.fg_product_id, 'type': 'fg'}, {'_id': 0})
        # Don't raise error if not found — catalog can have products not in FG yet

    # Check duplicate (same account + sku)
    if await db.marketing_creator_catalog.find_one({'account_id': data.account_id, 'sku': data.sku}):
        raise HTTPException(400, f"SKU '{data.sku}' sudah ada di katalog akun ini")

    item = {
        'id': _uid(),
        'account_id': data.account_id,
        'account_name': account['account_name'],
        'fg_product_id': data.fg_product_id,
        'product_name': data.product_name,
        'sku': data.sku,
        'category': data.category or '',
        'unit_price': data.unit_price,
        'description': data.description or '',
        'is_active': data.is_active,
        'created_at': _now(),
        'created_by': _get_user(request).get('email', 'system'),
    }

    await db.marketing_creator_catalog.insert_one(item)

    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'create', 'marketing_creator_catalog',
        f"Added catalog item: {data.product_name} ({data.sku})"
    )

    return serialize_doc({'message': 'Produk berhasil ditambahkan ke katalog', 'item': item})


@router.put('/kol/catalog/{item_id}')
async def update_catalog_item(item_id: str, data: CatalogItemCreate, request: Request):
    """Admin updates a catalog item"""
    await require_auth(request)
    db = get_db()

    item = await db.marketing_creator_catalog.find_one({'id': item_id}, {'_id': 0})
    if not item:
        raise HTTPException(404, 'Item katalog tidak ditemukan')

    update_data = {
        'product_name': data.product_name,
        'sku': data.sku,
        'category': data.category or '',
        'unit_price': data.unit_price,
        'description': data.description or '',
        'is_active': data.is_active,
        'fg_product_id': data.fg_product_id,
        'updated_at': _now(),
    }

    await db.marketing_creator_catalog.update_one({'id': item_id}, {'$set': update_data})
    updated = await db.marketing_creator_catalog.find_one({'id': item_id}, {'_id': 0})
    return serialize_doc({'message': 'Item katalog diupdate', 'item': updated})


@router.delete('/kol/catalog/{item_id}')
async def remove_catalog_item(item_id: str, request: Request):
    """Admin removes a product from catalog (sets is_active=false)"""
    await require_auth(request)
    db = get_db()

    item = await db.marketing_creator_catalog.find_one({'id': item_id}, {'_id': 0})
    if not item:
        raise HTTPException(404, 'Item katalog tidak ditemukan')

    await db.marketing_creator_catalog.update_one(
        {'id': item_id},
        {'$set': {'is_active': False, 'updated_at': _now()}}
    )
    return serialize_doc({'message': 'Item katalog dinonaktifkan'})


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — FG PRODUCTS (for catalog linking)
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/kol/fg-products')
async def list_fg_products(request: Request, search: Optional[str] = Query(None)):
    """Admin lists FG products from production system for catalog linking"""
    await require_auth(request)
    db = get_db()

    query = {'type': 'fg'}
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'code': {'$regex': search, '$options': 'i'}},
        ]

    materials = await db.rahaza_materials.find(query, {'_id': 0}).sort('name', 1).limit(100).to_list(500)

    # Add stock info
    default_loc = await db.rahaza_locations.find_one({'active': True}, {'_id': 0})
    loc_id = default_loc['id'] if default_loc else None

    for mat in materials:
        stock_doc = await db.rahaza_material_stock.find_one(
            {'material_id': mat['id'], 'location_id': loc_id}, {'_id': 0}
        )
        mat['stock_qty'] = float(stock_doc.get('qty', 0)) if stock_doc else 0

    return serialize_doc(materials)


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — LEADERBOARD
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/kol/leaderboard')
async def get_leaderboard(
    request: Request,
    month: Optional[str] = Query(None, description="YYYY-MM, defaults to current month"),
):
    """Creator leaderboard ranked by revenue for the month"""
    await require_auth(request)
    db = get_db()

    if not month:
        month = _now().strftime('%Y-%m')

    date_from = f'{month}-01'
    year, mon = int(month.split('-')[0]), int(month.split('-')[1])
    next_month = datetime(year, mon, 1, tzinfo=timezone.utc) + timedelta(days=32)
    date_to = (next_month.replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d')

    creators = await db.marketing_kol_creators.find(
        {'status': 'active'}, {'_id': 0, 'login_password_hash': 0}
    ).to_list(500)

    leaderboard = []
    for creator in creators:
        sessions = await db.marketing_creator_sessions.find(
            {'creator_id': creator['id'], 'date': {'$gte': date_from, '$lte': date_to}},
            {'_id': 0}
        ).to_list(500)

        total_revenue = round(sum(s.get('revenue', 0) for s in sessions))
        total_viewers = sum(s.get('viewers', 0) for s in sessions)
        total_orders = sum(s.get('orders', 0) for s in sessions)
        total_sessions = len(sessions)

        kpi = creator.get('kpi_targets', {})
        leaderboard.append({
            'creator_id': creator['id'],
            'creator_code': creator['creator_code'],
            'name': creator['name'],
            'platforms': creator.get('platforms', {}),
            'total_revenue': total_revenue,
            'total_viewers': total_viewers,
            'total_orders': total_orders,
            'total_sessions': total_sessions,
            'kpi_revenue_target': kpi.get('monthly_revenue', 0),
            'kpi_revenue_pct': round(total_revenue / kpi['monthly_revenue'] * 100, 1) if kpi.get('monthly_revenue') else None,
        })

    # Sort by revenue descending
    leaderboard.sort(key=lambda x: x['total_revenue'], reverse=True)
    for i, entry in enumerate(leaderboard):
        entry['rank'] = i + 1

    return serialize_doc({
        'month': month,
        'leaderboard': leaderboard
    })


# ══════════════════════════════════════════════════════════════════════════════
# SEED DATA
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/kol/seed-demo')
async def seed_kol_demo(request: Request):
    """Seed demo KOL creators for testing"""
    await require_auth(request)
    db = get_db()

    # Get an account to assign
    account = await db.marketing_platform_accounts.find_one({'status': 'active'}, {'_id': 0})
    if not account:
        raise HTTPException(400, 'Tidak ada akun aktif. Seed akun terlebih dahulu.')

    demo_creators = [
        {
            'id': _uid(),
            'creator_code': 'KOL-001',
            'name': 'Ayu Dewi',
            'login_email': 'ayu.creator@demo.com',
            'login_password_hash': hash_password('Creator@123'),
            'phone': '08111222333',
            'platforms': {'tiktok': '@ayu_fashion', 'shopee': 'ayu_dewi_store'},
            'assigned_account_ids': [account['id']],
            'kpi_targets': {
                'monthly_revenue': 50000000,
                'monthly_sessions': 12,
                'monthly_viewers': 80000,
            },
            'notes': 'Top creator fashion',
            'status': 'active',
            'last_login_at': None,
            'created_at': _now(),
            'created_by': 'seed',
            'updated_at': _now(),
        },
        {
            'id': _uid(),
            'creator_code': 'KOL-002',
            'name': 'Budi Santoso',
            'login_email': 'budi.creator@demo.com',
            'login_password_hash': hash_password('Creator@123'),
            'phone': '08222333444',
            'platforms': {'tiktok': '@budi_daily', 'instagram': 'budi.santoso'},
            'assigned_account_ids': [account['id']],
            'kpi_targets': {
                'monthly_revenue': 30000000,
                'monthly_sessions': 8,
                'monthly_viewers': 50000,
            },
            'notes': 'Lifestyle creator',
            'status': 'active',
            'last_login_at': None,
            'created_at': _now(),
            'created_by': 'seed',
            'updated_at': _now(),
        },
        {
            'id': _uid(),
            'creator_code': 'KOL-003',
            'name': 'Citra Lestari',
            'login_email': 'citra.creator@demo.com',
            'login_password_hash': hash_password('Creator@123'),
            'phone': '08333444555',
            'platforms': {'shopee': 'citra_official', 'tiktok': '@citra_style'},
            'assigned_account_ids': [account['id']],
            'kpi_targets': {
                'monthly_revenue': 40000000,
                'monthly_sessions': 10,
                'monthly_viewers': 60000,
            },
            'notes': 'Beauty & fashion',
            'status': 'active',
            'last_login_at': None,
            'created_at': _now(),
            'created_by': 'seed',
            'updated_at': _now(),
        },
    ]

    created = 0
    for c in demo_creators:
        if not await db.marketing_kol_creators.find_one({'creator_code': c['creator_code']}):
            await db.marketing_kol_creators.insert_one(c)
            created += 1

    # Seed some sessions for current month
    month = _now().strftime('%Y-%m')
    created_sessions = 0
    for idx, c in enumerate(demo_creators):
        creator_doc = await db.marketing_kol_creators.find_one({'creator_code': c['creator_code']}, {'_id': 0})
        if not creator_doc:
            continue
        for day in [5, 12, 19]:
            date_str = f"{month}-{day:02d}"
            if not await db.marketing_creator_sessions.find_one({'creator_id': creator_doc['id'], 'date': date_str}):
                await db.marketing_creator_sessions.insert_one({
                    'id': _uid(),
                    'creator_id': creator_doc['id'],
                    'creator_name': creator_doc['name'],
                    'creator_code': creator_doc['creator_code'],
                    'account_id': account['id'],
                    'account_name': account['account_name'],
                    'platform': account['platform'],
                    'date': date_str,
                    'session_name': f"Live Sesi {day}",
                    'duration_minutes': 90 + idx * 30,
                    'viewers': 1500 + idx * 500 + day * 100,
                    'peak_viewers': 2000 + idx * 600 + day * 150,
                    'revenue': (5000000 + idx * 2000000 + day * 100000),
                    'orders': 50 + idx * 20 + day,
                    'items_promoted': ['Kemeja Batik', 'Celana Chino'],
                    'notes': 'Sesi demo',
                    'created_at': _now(),
                    'created_by': 'seed',
                })
                created_sessions += 1

    return serialize_doc({
        'message': 'Demo KOL data seeded',
        'creators_created': created,
        'sessions_created': created_sessions,
        'catalog_created': await _seed_kol_catalog(db, account['id']),
        'note': 'Default password telah di-set untuk akun demo. Hubungi admin untuk credential.',
    })


async def _seed_kol_catalog(db, account_id: str) -> int:
    """Seed demo produk ke marketing_creator_catalog untuk testing request flow."""
    demo_products = [
        {'sku': 'KOL-PROD-001', 'product_name': 'Kemeja Batik Premium',  'category': 'Atasan',   'price': 189000, 'description': 'Kemeja batik motif kawung premium cotton'},
        {'sku': 'KOL-PROD-002', 'product_name': 'Celana Chino Slim Fit', 'category': 'Bawahan',  'price': 249000, 'description': 'Celana chino slim fit berbagai warna'},
        {'sku': 'KOL-PROD-003', 'product_name': 'Gaun Dress Floral',     'category': 'Dress',    'price': 329000, 'description': 'Gaun motif bunga untuk casual & formal'},
        {'sku': 'KOL-PROD-004', 'product_name': 'Blouse Polos Linen',    'category': 'Atasan',   'price': 159000, 'description': 'Blouse bahan linen adem untuk sehari-hari'},
        {'sku': 'KOL-PROD-005', 'product_name': 'Rok Midi Plisket',      'category': 'Bawahan',  'price': 199000, 'description': 'Rok midi plisket elegan'},
        {'sku': 'KOL-PROD-006', 'product_name': 'Jaket Denim Classic',   'category': 'Outerwear','price': 379000, 'description': 'Jaket denim klasik unisex'},
    ]
    created = 0
    for p in demo_products:
        existing = await db.marketing_creator_catalog.find_one({'sku': p['sku'], 'account_id': account_id})
        if not existing:
            await db.marketing_creator_catalog.insert_one({
                'id': _uid(),
                'account_id': account_id,
                'sku': p['sku'],
                'product_name': p['product_name'],
                'category': p.get('category', ''),
                'description': p.get('description', ''),
                'price': p['price'],
                'fg_product_id': None,      # bisa di-link ke WMS nanti
                'images': [],
                'is_active': True,
                'stock_note': 'Ready stock',
                'created_at': _now(),
                'created_by': 'seed',
            })
            created += 1
    return created
