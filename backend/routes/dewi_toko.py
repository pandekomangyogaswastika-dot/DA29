"""
CV. Dewi Aditya — Phase 5 Sprint 32: Portal Toko Online
  - Product Catalog (SKU Master)
  - Channel Manager (Shopee / Tokopedia / TikTok Shop / Website) — MOCK mode
  - Dashboard aggregation

Collections:
- dewi_toko_products
- dewi_toko_channels
- dewi_toko_channel_syncs (audit log for sync attempts)

All write endpoints require internal auth. Channel sync runs in MOCK mode —
it simulates API calls and stamps last_sync_at. Real provider integration
will replace the `_mock_sync_provider(channel)` helper later.
"""
import os
import re
import random
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from pydantic import BaseModel, Field
from database import get_db
from auth import require_auth
from utils.helpers import _uid, _now, _clean, _clean_list

router = APIRouter(prefix='/api/dewi/toko', tags=['Dewi-Toko'])

PRODUCT_UPLOAD_ROOT = Path('/app/uploads/products')
PRODUCT_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
MAX_PHOTO_BYTES = 5 * 1024 * 1024
ALLOWED_MIMES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_EXT = {'jpg', 'jpeg', 'png', 'webp'}

SUPPORTED_CHANNELS = ['shopee', 'tokopedia', 'tiktok_shop', 'website']
CHANNEL_LABELS = {
    'shopee': 'Shopee',
    'tokopedia': 'Tokopedia',
    'tiktok_shop': 'TikTok Shop',
    'website': 'Website Sendiri',
}


# ══════════════════════════════════════════════════════════════════════════════
# SEED
# ══════════════════════════════════════════════════════════════════════════════

async def seed_toko_channels():
    """Idempotent: seed 4 preset channels with mock=True if empty."""
    db = get_db()
    # Batch fetch existing channel codes
    existing_codes = set()
    async for d in db.dewi_toko_channels.find(
        {'code': {'$in': list(SUPPORTED_CHANNELS)}}, {'_id': 0, 'code': 1}
    ):
        existing_codes.add(d['code'])
    for code in SUPPORTED_CHANNELS:
        if code in existing_codes:
            continue
        await db.dewi_toko_channels.insert_one({
            'id': _uid(),
            'code': code,
            'name': CHANNEL_LABELS[code],
            'enabled': False,
            'mock': True,
            'credentials': {
                'api_key': '',
                'api_secret': '',
                'shop_id': '',
                'webhook_url': '',
            },
            'last_sync_at': None,
            'last_sync_status': None,
            'last_sync_counts': {'products': 0, 'orders': 0, 'errors': 0},
            'fee_pct': 0.0,
            'commission_pct': 0.0,
            'notes': 'Mode MOCK — kredensial real belum dikonfigurasi.',
            'created_at': _now(),
            'updated_at': _now(),
        })


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCT CATALOG
# ══════════════════════════════════════════════════════════════════════════════

class ProductVariant(BaseModel):
    id: Optional[str] = None
    name: str = ''
    size: Optional[str] = None
    color: Optional[str] = None
    sku_suffix: Optional[str] = None
    stock: int = 0


class ChannelPrice(BaseModel):
    channel: str
    price: float = Field(..., ge=0)
    active: bool = True


class ProductIn(BaseModel):
    sku_code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2)
    description: Optional[str] = None
    category: Optional[str] = None
    base_price: float = Field(default=0, ge=0)
    cost_price: float = Field(default=0, ge=0)
    channel_prices: List[ChannelPrice] = Field(default_factory=list)
    variants: List[ProductVariant] = Field(default_factory=list)
    photos: List[str] = Field(default_factory=list)
    stock_total: int = Field(default=0, ge=0)
    weight_grams: Optional[int] = Field(default=None, ge=0)
    status: str = 'draft'
    tags: List[str] = Field(default_factory=list)


class ProductPatchIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    base_price: Optional[float] = Field(default=None, ge=0)
    cost_price: Optional[float] = Field(default=None, ge=0)
    channel_prices: Optional[List[ChannelPrice]] = None
    variants: Optional[List[ProductVariant]] = None
    photos: Optional[List[str]] = None
    stock_total: Optional[int] = Field(default=None, ge=0)
    weight_grams: Optional[int] = Field(default=None, ge=0)
    status: Optional[str] = None
    tags: Optional[List[str]] = None


@router.get('/products')
async def list_products(
    status: Optional[str] = None,
    search: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 200,
    user: dict = Depends(require_auth),
):
    db = get_db()
    q: Dict[str, Any] = {}
    if status and status != 'all':
        q['status'] = status
    if category:
        q['category'] = category
    if search:
        rx = {'$regex': re.escape(search), '$options': 'i'}
        q['$or'] = [{'sku_code': rx}, {'name': rx}]
    items = await db.dewi_toko_products.find(q).sort('updated_at', -1).to_list(length=min(max(limit, 1), 1000))
    return _clean_list(items)


@router.get('/products/{pid}')
async def get_product(pid: str, user: dict = Depends(require_auth)):
    db = get_db()
    p = await db.dewi_toko_products.find_one({'id': pid})
    if not p:
        raise HTTPException(404, 'Produk tidak ditemukan')
    return _clean(p)


@router.post('/products')
async def create_product(payload: ProductIn, user: dict = Depends(require_auth)):
    db = get_db()
    sku = payload.sku_code.strip().upper()
    existing = await db.dewi_toko_products.find_one({'sku_code': sku})
    if existing:
        raise HTTPException(400, f'SKU {sku} sudah terdaftar')
    # Ensure variant ids
    variants = [v.model_dump() for v in payload.variants]
    for v in variants:
        if not v.get('id'):
            v['id'] = _uid()
    doc = payload.model_dump()
    doc.update({
        'id': _uid(),
        'sku_code': sku,
        'variants': variants,
        'channel_prices': [cp.model_dump() for cp in payload.channel_prices],
        'stock_reserved': 0,
        'sales_count_total': 0,
        'created_at': _now(),
        'updated_at': _now(),
        'created_by': user.get('name', 'System'),
    })
    await db.dewi_toko_products.insert_one(doc)
    return {'message': 'Produk berhasil dibuat', 'id': doc['id'], 'sku_code': sku}


@router.put('/products/{pid}')
async def update_product(pid: str, payload: ProductPatchIn, user: dict = Depends(require_auth)):
    db = get_db()
    p = await db.dewi_toko_products.find_one({'id': pid})
    if not p:
        raise HTTPException(404, 'Produk tidak ditemukan')
    patch = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    # Normalize nested models
    if 'variants' in patch:
        for v in patch['variants']:
            if not v.get('id'):
                v['id'] = _uid()
    if 'channel_prices' in patch:
        patch['channel_prices'] = [dict(cp) for cp in patch['channel_prices']]
    patch['updated_at'] = _now()
    await db.dewi_toko_products.update_one({'id': pid}, {'$set': patch})
    return {'message': 'Produk diperbarui'}


@router.delete('/products/{pid}')
async def delete_product(pid: str, user: dict = Depends(require_auth)):
    db = get_db()
    res = await db.dewi_toko_products.delete_one({'id': pid})
    if res.deleted_count == 0:
        raise HTTPException(404, 'Produk tidak ditemukan')
    return {'message': 'Produk dihapus'}


@router.post('/products/{pid}/photos')
async def upload_product_photo(
    pid: str,
    file: UploadFile = File(...),
    user: dict = Depends(require_auth),
):
    db = get_db()
    prod = await db.dewi_toko_products.find_one({'id': pid})
    if not prod:
        raise HTTPException(404, 'Produk tidak ditemukan')
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(415, f'Hanya {sorted(ALLOWED_MIMES)} diizinkan')
    data = await file.read()
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(413, 'Ukuran file > 5MB')
    if len(data) < 100:
        raise HTTPException(400, 'File terlalu kecil')

    ext = 'jpg'
    if file.filename and '.' in file.filename:
        candidate = file.filename.rsplit('.', 1)[-1].lower()
        candidate = re.sub(r'[^a-z0-9]', '', candidate)
        if candidate in ALLOWED_EXT:
            ext = candidate
    folder = PRODUCT_UPLOAD_ROOT / pid
    folder.mkdir(parents=True, exist_ok=True)
    fname = f'{uuid.uuid4().hex}.{ext}'
    with open(folder / fname, 'wb') as f:
        f.write(data)
    url = f'/api/uploads/products/{pid}/{fname}'

    await db.dewi_toko_products.update_one(
        {'id': pid},
        {'$push': {'photos': url}, '$set': {'updated_at': _now()}},
    )
    return {'url': url, 'size': len(data)}


class RemovePhotoIn(BaseModel):
    url: str


@router.post('/products/{pid}/photos/remove')
async def remove_product_photo(pid: str, payload: RemovePhotoIn, user: dict = Depends(require_auth)):
    db = get_db()
    prod = await db.dewi_toko_products.find_one({'id': pid})
    if not prod:
        raise HTTPException(404, 'Produk tidak ditemukan')
    await db.dewi_toko_products.update_one(
        {'id': pid},
        {'$pull': {'photos': payload.url}, '$set': {'updated_at': _now()}},
    )
    # Also try to delete the file best-effort
    try:
        if payload.url.startswith('/api/uploads/products/'):
            rel = payload.url.replace('/api/uploads/products/', '')
            fp = PRODUCT_UPLOAD_ROOT / rel
            if fp.exists() and fp.is_file():
                os.unlink(fp)
    except Exception:
        pass
    return {'message': 'Foto dihapus'}


# ══════════════════════════════════════════════════════════════════════════════
# CHANNEL MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class ChannelUpdateIn(BaseModel):
    enabled: Optional[bool] = None
    credentials: Optional[Dict[str, Any]] = None
    fee_pct: Optional[float] = Field(default=None, ge=0, le=100)
    commission_pct: Optional[float] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = None


def _mask_creds(creds: dict) -> dict:
    if not creds:
        return {}
    out = {}
    for k, v in creds.items():
        if not v:
            out[k] = ''
        elif k in {'api_key', 'api_secret'} and isinstance(v, str):
            out[k] = v[:4] + '***' + v[-2:] if len(v) > 8 else '***'
        else:
            out[k] = v
    return out


@router.get('/channels')
async def list_channels(user: dict = Depends(require_auth)):
    db = get_db()
    await seed_toko_channels()
    items = await db.dewi_toko_channels.find({}).sort('code', 1).to_list(length=50)
    for it in items:
        it['credentials'] = _mask_creds(it.get('credentials'))
    return _clean_list(items)


@router.put('/channels/{code}')
async def update_channel(code: str, payload: ChannelUpdateIn, user: dict = Depends(require_auth)):
    db = get_db()
    ch = await db.dewi_toko_channels.find_one({'code': code})
    if not ch:
        raise HTTPException(404, 'Channel tidak ditemukan')
    patch = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if 'credentials' in patch:
        # Merge credentials rather than overwrite to avoid losing secrets not provided
        merged = dict(ch.get('credentials') or {})
        for k, v in (patch['credentials'] or {}).items():
            if v == '' and k in {'api_key', 'api_secret'}:
                # explicit empty clears — otherwise keep old
                merged[k] = ''
            elif v is not None and not (isinstance(v, str) and v.startswith('***')):
                merged[k] = v
        patch['credentials'] = merged
    patch['updated_at'] = _now()
    await db.dewi_toko_channels.update_one({'code': code}, {'$set': patch})
    return {'message': 'Channel diperbarui'}


def _mock_sync_provider(channel: dict) -> dict:
    """
    Simulate an external marketplace sync call.
    Returns counts for products/orders/errors.
    Real provider integration will replace this function.
    """
    code = channel.get('code')
    # Deterministic-ish but varying counts per call
    return {
        'products': random.randint(3, 12),
        'orders': random.randint(0, 8),
        'errors': 0 if channel.get('enabled') else 0,
        'mock': True,
        'channel': code,
    }


@router.post('/channels/{code}/sync')
async def sync_channel(code: str, user: dict = Depends(require_auth)):
    db = get_db()
    ch = await db.dewi_toko_channels.find_one({'code': code})
    if not ch:
        raise HTTPException(404, 'Channel tidak ditemukan')
    if not ch.get('enabled'):
        raise HTTPException(400, 'Channel belum di-enable. Aktifkan dulu sebelum sync.')
    started = _now()
    try:
        # Mock provider call
        counts = _mock_sync_provider(ch)
        finished = _now()
        log_doc = {
            'id': _uid(),
            'channel_code': code,
            'status': 'success',
            'started_at': started,
            'finished_at': finished,
            'duration_ms': int((finished - started).total_seconds() * 1000),
            'counts': counts,
            'mock': True,
            'triggered_by': user.get('name', 'System'),
        }
        await db.dewi_toko_channel_syncs.insert_one(log_doc)
        await db.dewi_toko_channels.update_one(
            {'code': code},
            {'$set': {
                'last_sync_at': finished,
                'last_sync_status': 'success',
                'last_sync_counts': counts,
                'updated_at': finished,
            }},
        )
        return {
            'message': f'Sync {CHANNEL_LABELS.get(code, code)} berhasil (MOCK)',
            'counts': counts,
            'duration_ms': log_doc['duration_ms'],
        }
    except Exception as e:
        finished = _now()
        await db.dewi_toko_channel_syncs.insert_one({
            'id': _uid(),
            'channel_code': code,
            'status': 'failed',
            'started_at': started,
            'finished_at': finished,
            'error': str(e),
            'triggered_by': user.get('name', 'System'),
        })
        await db.dewi_toko_channels.update_one(
            {'code': code},
            {'$set': {'last_sync_status': 'failed', 'last_sync_at': finished}},
        )
        raise HTTPException(500, f'Sync gagal: {e}')


@router.get('/channels/{code}/sync-history')
async def channel_sync_history(code: str, limit: int = 20, user: dict = Depends(require_auth)):
    db = get_db()
    items = await db.dewi_toko_channel_syncs.find({'channel_code': code}).sort('started_at', -1).to_list(length=min(max(limit, 1), 100))
    return _clean_list(items)


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/dashboard')
async def toko_dashboard(user: dict = Depends(require_auth)):
    db = get_db()
    await seed_toko_channels()

    # Product stats
    total_products = await db.dewi_toko_products.count_documents({})
    active_products = await db.dewi_toko_products.count_documents({'status': 'active'})
    draft_products = await db.dewi_toko_products.count_documents({'status': 'draft'})

    # Low stock (< 10 total stock)
    low_stock = await db.dewi_toko_products.count_documents({'status': 'active', 'stock_total': {'$lt': 10}})

    # Total inventory value (sum of stock_total * base_price)
    pipeline_value = [
        {'$match': {'status': {'$in': ['active', 'draft']}}},
        {'$group': {'_id': None, 'total': {'$sum': {'$multiply': ['$stock_total', '$base_price']}}}},
    ]
    total_value = 0
    async for d in db.dewi_toko_products.aggregate(pipeline_value):
        total_value = float(d.get('total') or 0)

    # Channels
    channels = await db.dewi_toko_channels.find({}).sort('code', 1).to_list(length=50)
    channel_cards = []
    enabled_channels = 0
    for c in channels:
        if c.get('enabled'):
            enabled_channels += 1
        channel_cards.append({
            'code': c.get('code'),
            'name': c.get('name'),
            'enabled': c.get('enabled'),
            'last_sync_at': c.get('last_sync_at'),
            'last_sync_counts': c.get('last_sync_counts') or {},
        })

    # Top 5 products by sales_count_total
    top_products = await db.dewi_toko_products.find({}).sort('sales_count_total', -1).limit(5).to_list(length=5)
    top_products = _clean_list(top_products)

    # Recent sync log (5 newest across channels)
    recent_syncs = await db.dewi_toko_channel_syncs.find({}).sort('started_at', -1).limit(5).to_list(length=5)
    recent_syncs = _clean_list(recent_syncs)

    return {
        'products': {
            'total': total_products,
            'active': active_products,
            'draft': draft_products,
            'low_stock': low_stock,
            'inventory_value': total_value,
        },
        'channels': {
            'total': len(channels),
            'enabled': enabled_channels,
            'cards': channel_cards,
        },
        'top_products': top_products,
        'recent_syncs': recent_syncs,
        'mock_mode': True,  # clear indicator for UI
    }


# ══════════════════════════════════════════════════════════════════════════════
# FLASHSALE & PRICING
# ══════════════════════════════════════════════════════════════════════════════

class FlashsaleProductItem(BaseModel):
    product_id: Optional[str] = None
    sku_code: str
    name: Optional[str] = None
    original_price: float = Field(default=0.0, ge=0)
    flashsale_price: float = Field(default=0.0, ge=0)
    discount_pct: float = Field(default=0.0, ge=0, le=100)
    quota: int = Field(default=0, ge=0)

class FlashsaleIn(BaseModel):
    name: str = Field(..., min_length=2)
    channel_code: str = 'shopee'
    start_at: str  # ISO datetime string
    end_at: str    # ISO datetime string
    products: List[FlashsaleProductItem] = Field(default_factory=list)
    notes: Optional[str] = None

class FlashsalePatchIn(BaseModel):
    name: Optional[str] = None
    channel_code: Optional[str] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    products: Optional[List[FlashsaleProductItem]] = None
    notes: Optional[str] = None
    status: Optional[str] = None


@router.get('/flashsales')
async def list_flashsales(
    status: Optional[str] = None,
    channel_code: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(require_auth)
):
    db = get_db()
    filt: dict = {}
    if status:
        filt['status'] = status
    if channel_code:
        filt['channel_code'] = channel_code
    items = await db.dewi_toko_flashsales.find(filt).sort('start_at', -1).to_list(length=limit)
    return _clean_list(items)


@router.get('/flashsales/{flashsale_id}')
async def get_flashsale(flashsale_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_toko_flashsales.find_one({'id': flashsale_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Flashsale tidak ditemukan')
    return _clean(doc)


@router.post('/flashsales', status_code=201)
async def create_flashsale(payload: FlashsaleIn, user=Depends(require_auth)):
    db = get_db()
    if payload.channel_code not in SUPPORTED_CHANNELS:
        raise HTTPException(status_code=422, detail=f'Channel tidak valid: {SUPPORTED_CHANNELS}')
    doc = {
        'id': _uid(),
        'name': payload.name,
        'channel_code': payload.channel_code,
        'start_at': payload.start_at,
        'end_at': payload.end_at,
        'products': [p.model_dump() for p in payload.products],
        'notes': payload.notes,
        'status': 'draft',
        'created_by': user.get('id'),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.dewi_toko_flashsales.insert_one(doc)
    return {'message': 'Flashsale dibuat', 'id': doc['id']}


@router.put('/flashsales/{flashsale_id}')
async def update_flashsale(flashsale_id: str, payload: FlashsalePatchIn, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_toko_flashsales.find_one({'id': flashsale_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Flashsale tidak ditemukan')
    if doc['status'] == 'active':
        raise HTTPException(status_code=400, detail='Flashsale aktif tidak bisa diedit. Nonaktifkan dulu.')
    patch = payload.model_dump(exclude_none=True)
    if 'products' in patch:
        patch['products'] = [p if isinstance(p, dict) else p.model_dump() for p in patch['products']]
    if not patch:
        raise HTTPException(status_code=422, detail='Tidak ada field yang diupdate')
    patch['updated_at'] = _now()
    await db.dewi_toko_flashsales.update_one({'id': flashsale_id}, {'$set': patch})
    return {'message': 'Flashsale diperbarui'}


@router.post('/flashsales/{flashsale_id}/activate')
async def toggle_flashsale(flashsale_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_toko_flashsales.find_one({'id': flashsale_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Flashsale tidak ditemukan')
    new_status = 'active' if doc['status'] != 'active' else 'draft'
    await db.dewi_toko_flashsales.update_one(
        {'id': flashsale_id},
        {'$set': {'status': new_status, 'updated_at': _now()}}
    )
    return {'message': f'Status flashsale: {new_status}', 'status': new_status}


@router.delete('/flashsales/{flashsale_id}')
async def delete_flashsale(flashsale_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_toko_flashsales.find_one({'id': flashsale_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Flashsale tidak ditemukan')
    if doc['status'] == 'active':
        raise HTTPException(status_code=400, detail='Nonaktifkan flashsale sebelum menghapus')
    await db.dewi_toko_flashsales.delete_one({'id': flashsale_id})
    return {'message': 'Flashsale dihapus'}
