"""
CV. Dewi Aditya — Phase 5B: KOL / Kreator Management
  - Creator database (KOL profiles, categories)
  - Deal management (product deals with creators)
  - Sample tracking (samples sent to creators)

Collections:
- dewi_kol_creators
- dewi_kol_deals
- dewi_kol_samples
"""
import re
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from database import get_db
from auth import require_auth
from utils.helpers import _uid, _now, _clean, _clean_list, _next_code

router = APIRouter(prefix='/api/dewi/kol', tags=['Dewi-KOL'])

CREATOR_CATEGORIES = ['power_partner', 'potential', 'viral_maker', 'active', 'passive']
CHANNEL_TYPES = ['shopee', 'tokopedia', 'tiktok_shop', 'instagram', 'youtube', 'other']
DEAL_TYPES = ['live_stream', 'tiktok_video', 'feed_post', 'story', 'review']
SAMPLE_STATUSES = ['draft', 'shipped', 'received', 'feedback', 'done', 'cancelled']
DEAL_STATUSES = ['draft', 'active', 'completed', 'cancelled']

# ── Models ────────────────────────────────────────────────────────────────────

class CreatorIn(BaseModel):
    name: str = Field(..., min_length=2)
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    channel_type: str = 'tiktok_shop'
    category: str = 'active'
    username: Optional[str] = None
    followers: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None
    status: str = 'active'

class CreatorPatchIn(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    channel_type: Optional[str] = None
    category: Optional[str] = None
    username: Optional[str] = None
    followers: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None
    status: Optional[str] = None

class DealProductItem(BaseModel):
    sku_code: str
    product_name: Optional[str] = None

class DealIn(BaseModel):
    creator_id: str
    products: List[DealProductItem] = Field(default_factory=list)
    deal_type: str = 'tiktok_video'
    commission_pct: float = Field(default=0.0, ge=0, le=100)
    notes: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: str = 'draft'

class DealPatchIn(BaseModel):
    products: Optional[List[DealProductItem]] = None
    deal_type: Optional[str] = None
    commission_pct: Optional[float] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None
    result_notes: Optional[str] = None

class SampleIn(BaseModel):
    creator_id: str
    deal_id: Optional[str] = None
    sku_code: str
    product_name: Optional[str] = None
    qty: int = Field(default=1, ge=1)
    notes: Optional[str] = None

class SamplePatchIn(BaseModel):
    tracking_number: Optional[str] = None
    courier: Optional[str] = None
    status: Optional[str] = None
    feedback_notes: Optional[str] = None
    sent_at: Optional[str] = None
    received_at: Optional[str] = None

# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_creator_or_404(db, creator_id: str):
    doc = await db.dewi_kol_creators.find_one({'id': creator_id})
    if not doc:
        raise HTTPException(status_code=404, detail='KOL/Kreator tidak ditemukan')
    return doc

# ── CREATORS ─────────────────────────────────────────────────────────────────

@router.get('/creators')
async def list_creators(
    category: Optional[str] = None,
    channel_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    user=Depends(require_auth)
):
    db = get_db()
    filt: dict = {}
    if category:
        filt['category'] = category
    if channel_type:
        filt['channel_type'] = channel_type
    if status:
        filt['status'] = status
    if search:
        filt['$or'] = [
            {'name': {'$regex': re.escape(search), '$options': 'i'}},
            {'username': {'$regex': re.escape(search), '$options': 'i'}},
            {'city': {'$regex': re.escape(search), '$options': 'i'}},
        ]
    items = await db.dewi_kol_creators.find(filt).sort('name', 1).to_list(length=limit)
    return _clean_list(items)


@router.get('/creators/{creator_id}')
async def get_creator(creator_id: str, user=Depends(require_auth)):
    db = get_db()
    return _clean(await _get_creator_or_404(db, creator_id))


@router.post('/creators', status_code=201)
async def create_creator(payload: CreatorIn, user=Depends(require_auth)):
    db = get_db()
    if payload.category not in CREATOR_CATEGORIES:
        raise HTTPException(status_code=422, detail=f'Kategori tidak valid. Pilihan: {CREATOR_CATEGORIES}')
    if payload.channel_type not in CHANNEL_TYPES:
        raise HTTPException(status_code=422, detail=f'Channel type tidak valid.')
    doc = {
        'id': _uid(),
        'name': payload.name,
        'phone': payload.phone,
        'address': payload.address,
        'city': payload.city,
        'channel_type': payload.channel_type,
        'category': payload.category,
        'username': payload.username,
        'followers': payload.followers,
        'notes': payload.notes,
        'status': payload.status,
        'total_deals': 0,
        'total_samples_sent': 0,
        'created_by': user.get('id'),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.dewi_kol_creators.insert_one(doc)
    return {'message': 'Kreator berhasil ditambahkan', 'id': doc['id']}


@router.put('/creators/{creator_id}')
async def update_creator(creator_id: str, payload: CreatorPatchIn, user=Depends(require_auth)):
    db = get_db()
    await _get_creator_or_404(db, creator_id)
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not patch:
        raise HTTPException(status_code=422, detail='Tidak ada field yang diupdate')
    patch['updated_at'] = _now()
    await db.dewi_kol_creators.update_one({'id': creator_id}, {'$set': patch})
    return {'message': 'Kreator diperbarui'}


@router.delete('/creators/{creator_id}')
async def delete_creator(creator_id: str, user=Depends(require_auth)):
    db = get_db()
    await _get_creator_or_404(db, creator_id)
    await db.dewi_kol_creators.delete_one({'id': creator_id})
    return {'message': 'Kreator dihapus'}


# ── DEALS ─────────────────────────────────────────────────────────────────────

@router.get('/deals')
async def list_deals(
    creator_id: Optional[str] = None,
    status: Optional[str] = None,
    deal_type: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    user=Depends(require_auth)
):
    db = get_db()
    filt: dict = {}
    if creator_id:
        filt['creator_id'] = creator_id
    if status:
        filt['status'] = status
    if deal_type:
        filt['deal_type'] = deal_type
    items = await db.dewi_kol_deals.find(filt).sort('created_at', -1).to_list(length=limit)
    return _clean_list(items)


@router.get('/deals/{deal_id}')
async def get_deal(deal_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_kol_deals.find_one({'id': deal_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Deal tidak ditemukan')
    return _clean(doc)


@router.post('/deals', status_code=201)
async def create_deal(payload: DealIn, user=Depends(require_auth)):
    db = get_db()
    creator = await _get_creator_or_404(db, payload.creator_id)
    if payload.deal_type not in DEAL_TYPES:
        raise HTTPException(status_code=422, detail=f'Deal type tidak valid. Pilihan: {DEAL_TYPES}')
    code = await _next_code(db, 'DEAL', 'dewi_kol_deals', 'deal_code')
    doc = {
        'id': _uid(),
        'deal_code': code,
        'creator_id': payload.creator_id,
        'creator_name': creator['name'],
        'creator_category': creator.get('category', 'active'),
        'products': [p.model_dump() for p in payload.products],
        'deal_type': payload.deal_type,
        'commission_pct': payload.commission_pct,
        'notes': payload.notes,
        'start_date': payload.start_date,
        'end_date': payload.end_date,
        'status': payload.status,
        'result_notes': None,
        'created_by': user.get('id'),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.dewi_kol_deals.insert_one(doc)
    # Update creator stats
    await db.dewi_kol_creators.update_one({'id': payload.creator_id}, {'$inc': {'total_deals': 1}})
    return {'message': 'Deal dibuat', 'id': doc['id'], 'deal_code': code}


@router.put('/deals/{deal_id}')
async def update_deal(deal_id: str, payload: DealPatchIn, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_kol_deals.find_one({'id': deal_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Deal tidak ditemukan')
    patch = payload.model_dump(exclude_none=True)
    if 'products' in patch:
        patch['products'] = [p if isinstance(p, dict) else p for p in patch['products']]
    if not patch:
        raise HTTPException(status_code=422, detail='Tidak ada field yang diupdate')
    patch['updated_at'] = _now()
    await db.dewi_kol_deals.update_one({'id': deal_id}, {'$set': patch})
    return {'message': 'Deal diperbarui'}


@router.delete('/deals/{deal_id}')
async def delete_deal(deal_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_kol_deals.find_one({'id': deal_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Deal tidak ditemukan')
    await db.dewi_kol_deals.delete_one({'id': deal_id})
    return {'message': 'Deal dihapus'}


# ── SAMPLES ───────────────────────────────────────────────────────────────────

@router.get('/samples')
async def list_samples(
    creator_id: Optional[str] = None,
    status: Optional[str] = None,
    deal_id: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    user=Depends(require_auth)
):
    db = get_db()
    filt: dict = {}
    if creator_id:
        filt['creator_id'] = creator_id
    if status:
        filt['status'] = status
    if deal_id:
        filt['deal_id'] = deal_id
    items = await db.dewi_kol_samples.find(filt).sort('created_at', -1).to_list(length=limit)
    return _clean_list(items)


@router.post('/samples', status_code=201)
async def create_sample(payload: SampleIn, user=Depends(require_auth)):
    db = get_db()
    creator = await _get_creator_or_404(db, payload.creator_id)
    code = await _next_code(db, 'SMPL', 'dewi_kol_samples', 'sample_code')
    doc = {
        'id': _uid(),
        'sample_code': code,
        'creator_id': payload.creator_id,
        'creator_name': creator['name'],
        'deal_id': payload.deal_id,
        'sku_code': payload.sku_code.upper(),
        'product_name': payload.product_name,
        'qty': payload.qty,
        'notes': payload.notes,
        'status': 'draft',
        'tracking_number': None,
        'courier': None,
        'feedback_notes': None,
        'sent_at': None,
        'received_at': None,
        'created_by': user.get('id'),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.dewi_kol_samples.insert_one(doc)
    await db.dewi_kol_creators.update_one({'id': payload.creator_id}, {'$inc': {'total_samples_sent': 1}})
    return {'message': 'Sample request dibuat', 'id': doc['id'], 'sample_code': code}


@router.put('/samples/{sample_id}')
async def update_sample(sample_id: str, payload: SamplePatchIn, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_kol_samples.find_one({'id': sample_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Sample tidak ditemukan')
    patch = payload.model_dump(exclude_none=True)
    if not patch:
        raise HTTPException(status_code=422, detail='Tidak ada field yang diupdate')
    # Auto-stamp sent_at when status=shipped
    if patch.get('status') == 'shipped' and not doc.get('sent_at'):
        patch['sent_at'] = _now().isoformat()
    if patch.get('status') == 'received' and not doc.get('received_at'):
        patch['received_at'] = _now().isoformat()
    patch['updated_at'] = _now()
    await db.dewi_kol_samples.update_one({'id': sample_id}, {'$set': patch})
    return {'message': 'Sample diperbarui'}


@router.delete('/samples/{sample_id}')
async def delete_sample(sample_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_kol_samples.find_one({'id': sample_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Sample tidak ditemukan')
    await db.dewi_kol_samples.delete_one({'id': sample_id})
    return {'message': 'Sample dihapus'}


# ── SUMMARY ───────────────────────────────────────────────────────────────────

@router.get('/summary')
async def kol_summary(user=Depends(require_auth)):
    db = get_db()
    total_creators = await db.dewi_kol_creators.count_documents({'status': 'active'})
    total_deals = await db.dewi_kol_deals.count_documents({'status': 'active'})
    pending_samples = await db.dewi_kol_samples.count_documents({'status': {'$in': ['draft', 'shipped']}})
    return {
        'total_creators': total_creators,
        'total_deals_active': total_deals,
        'pending_samples': pending_samples,
    }
