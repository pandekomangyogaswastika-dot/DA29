"""
CV. Dewi Aditya — Phase 5B: Returns, Refunds & Customer Service
  - Return cases (expedition-return vs customer-refund)
  - Decision workflow: reship / refund / reject
  - CS Reviews: customer review management

Collections:
- dewi_toko_returns
- dewi_toko_reviews
  **DEPRECATED (P1.D 2026-05-23)** — dual-write to marketing_returns / marketing_reviews SSOT.
"""
import re
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from database import get_db
from auth import require_auth
from utils.helpers import _uid, _now, _clean, _clean_list, _next_code
from routes._toko_adapter import toko_return_to_marketing, toko_review_to_marketing
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/dewi/toko', tags=['Dewi-Toko-CS'])


# P1.D: Dual-write helpers
async def _mirror_return(db, doc: dict):
    """Mirror dewi_toko_returns → marketing_returns (idempotent upsert)."""
    try:
        mirror = toko_return_to_marketing(doc)
        await db.marketing_returns.update_one(
            {"id": mirror["id"]},
            {"$set": mirror},
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"[P1.D] _mirror_return failed: {e}")


async def _mirror_review(db, doc: dict):
    """Mirror dewi_toko_reviews → marketing_reviews (idempotent upsert)."""
    try:
        mirror = toko_review_to_marketing(doc)
        await db.marketing_reviews.update_one(
            {"id": mirror["id"]},
            {"$set": mirror},
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"[P1.D] _mirror_review failed: {e}")


RETURN_TYPES = ['expedition_return', 'customer_refund']
RETURN_STATUSES = ['new', 'investigating', 'decision_made', 'resolved', 'closed']
DECISIONS = ['reship', 'refund', 'reject', 'pending']
REVIEW_STATUSES = ['unread', 'responded', 'flagged', 'resolved']

# ── Models ────────────────────────────────────────────────────────────────────

class ReturnIn(BaseModel):
    order_id: Optional[str] = None
    order_number: Optional[str] = None
    return_type: str = 'customer_refund'
    customer_name: str = Field(..., min_length=1)
    channel_code: Optional[str] = None
    reason: str = Field(..., min_length=2)
    evidence_notes: Optional[str] = None
    estimated_value: float = Field(default=0.0, ge=0)

class ReturnPatchIn(BaseModel):
    reason: Optional[str] = None
    evidence_notes: Optional[str] = None
    status: Optional[str] = None
    estimated_value: Optional[float] = Field(default=None, ge=0)

class ReturnDecisionIn(BaseModel):
    decision: str
    decision_notes: str = Field(..., min_length=2)
    tracking_number: Optional[str] = None  # for reship

class ReviewIn(BaseModel):
    channel_code: str = 'shopee'
    order_ref: Optional[str] = None
    customer_name: Optional[str] = None
    rating: int = Field(default=5, ge=1, le=5)
    review_text: str = Field(..., min_length=2)
    sku_code: Optional[str] = None

class ReviewResponseIn(BaseModel):
    response_text: str = Field(..., min_length=5)


# ── RETURNS ───────────────────────────────────────────────────────────────────

@router.get('/returns', deprecated=True)
async def list_returns(
    return_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    user=Depends(require_auth)
):
    db = get_db()
    filt: dict = {}
    if return_type:
        filt['return_type'] = return_type
    if status:
        filt['status'] = status
    if search:
        filt['$or'] = [
            {'customer_name': {'$regex': re.escape(search), '$options': 'i'}},
            {'return_code': {'$regex': re.escape(search), '$options': 'i'}},
            {'order_number': {'$regex': re.escape(search), '$options': 'i'}},
        ]
    items = await db.dewi_toko_returns.find(filt).sort('created_at', -1).to_list(length=limit)
    return _clean_list(items)


@router.get('/returns/summary', deprecated=True)
async def returns_summary(user=Depends(require_auth)):
    db = get_db()
    new_count = await db.dewi_toko_returns.count_documents({'status': 'new'})
    investigating = await db.dewi_toko_returns.count_documents({'status': 'investigating'})
    resolved = await db.dewi_toko_returns.count_documents({'status': {'$in': ['resolved', 'closed']}})
    low_reviews = await db.dewi_toko_reviews.count_documents({'rating': {'$lte': 3}, 'status': {'$in': ['unread', 'flagged']}})
    return {
        'new_returns': new_count,
        'investigating': investigating,
        'resolved': resolved,
        'low_reviews': low_reviews,
    }


@router.get('/returns/{return_id}', deprecated=True)
async def get_return(return_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_toko_returns.find_one({'id': return_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Return tidak ditemukan')
    return _clean(doc)


@router.post('/returns', status_code=201, deprecated=True)
async def create_return(payload: ReturnIn, user=Depends(require_auth)):
    db = get_db()
    if payload.return_type not in RETURN_TYPES:
        raise HTTPException(status_code=422, detail=f'Return type tidak valid: {RETURN_TYPES}')
    code = await _next_code(db, 'RET', 'dewi_toko_returns', 'return_code')
    doc = {
        'id': _uid(),
        'return_code': code,
        'order_id': payload.order_id,
        'order_number': payload.order_number,
        'return_type': payload.return_type,
        'customer_name': payload.customer_name,
        'channel_code': payload.channel_code,
        'reason': payload.reason,
        'evidence_notes': payload.evidence_notes,
        'estimated_value': payload.estimated_value,
        'status': 'new',
        'decision': 'pending',
        'decision_notes': None,
        'tracking_number': None,
        'resolved_at': None,
        'created_by': user.get('id'),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.dewi_toko_returns.insert_one(doc)
    await _mirror_return(db, doc)
    return {'message': 'Kasus return dibuat', 'id': doc['id'], 'return_code': code}


@router.put('/returns/{return_id}', deprecated=True)
async def update_return(return_id: str, payload: ReturnPatchIn, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_toko_returns.find_one({'id': return_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Return tidak ditemukan')
    patch = payload.model_dump(exclude_none=True)
    if not patch:
        raise HTTPException(status_code=422, detail='Tidak ada field yang diupdate')
    patch['updated_at'] = _now()
    await db.dewi_toko_returns.update_one({'id': return_id}, {'$set': patch})
    refreshed = await db.dewi_toko_returns.find_one({'id': return_id})
    if refreshed:
        await _mirror_return(db, refreshed)
    return {'message': 'Return diperbarui'}


@router.post('/returns/{return_id}/decision', deprecated=True)
async def make_return_decision(return_id: str, payload: ReturnDecisionIn, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_toko_returns.find_one({'id': return_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Return tidak ditemukan')
    if payload.decision not in DECISIONS:
        raise HTTPException(status_code=422, detail=f'Keputusan tidak valid: {DECISIONS}')
    patch = {
        'decision': payload.decision,
        'decision_notes': payload.decision_notes,
        'status': 'decision_made',
        'updated_at': _now(),
    }
    if payload.tracking_number:
        patch['tracking_number'] = payload.tracking_number
    if payload.decision in ['reship', 'refund', 'reject']:
        patch['status'] = 'resolved'
        patch['resolved_at'] = _now().isoformat()
    await db.dewi_toko_returns.update_one({'id': return_id}, {'$set': patch})
    refreshed = await db.dewi_toko_returns.find_one({'id': return_id})
    if refreshed:
        await _mirror_return(db, refreshed)
    return {'message': f'Keputusan: {payload.decision}'}


@router.delete('/returns/{return_id}', deprecated=True)
async def delete_return(return_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_toko_returns.find_one({'id': return_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Return tidak ditemukan')
    await db.dewi_toko_returns.delete_one({'id': return_id})
    return {'message': 'Return dihapus'}


# ── REVIEWS (CS) ──────────────────────────────────────────────────────────────

@router.get('/reviews', deprecated=True)
async def list_reviews(
    status: Optional[str] = None,
    channel_code: Optional[str] = None,
    min_rating: Optional[int] = Query(default=None, ge=1, le=5),
    max_rating: Optional[int] = Query(default=None, ge=1, le=5),
    limit: int = Query(default=100, ge=1, le=500),
    user=Depends(require_auth)
):
    db = get_db()
    filt: dict = {}
    if status:
        filt['status'] = status
    if channel_code:
        filt['channel_code'] = channel_code
    if min_rating is not None:
        filt.setdefault('rating', {})['$gte'] = min_rating
    if max_rating is not None:
        filt.setdefault('rating', {})['$lte'] = max_rating
    items = await db.dewi_toko_reviews.find(filt).sort('created_at', -1).to_list(length=limit)
    return _clean_list(items)


@router.post('/reviews', status_code=201, deprecated=True)
async def create_review(payload: ReviewIn, user=Depends(require_auth)):
    db = get_db()
    doc = {
        'id': _uid(),
        'channel_code': payload.channel_code,
        'order_ref': payload.order_ref,
        'customer_name': payload.customer_name,
        'rating': payload.rating,
        'review_text': payload.review_text,
        'sku_code': payload.sku_code,
        'status': 'unread',
        'response_text': None,
        'responded_at': None,
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.dewi_toko_reviews.insert_one(doc)
    await _mirror_review(db, doc)
    return {'message': 'Review dicatat', 'id': doc['id']}


@router.put('/reviews/{review_id}/respond', deprecated=True)
async def respond_review(review_id: str, payload: ReviewResponseIn, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_toko_reviews.find_one({'id': review_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Review tidak ditemukan')
    await db.dewi_toko_reviews.update_one(
        {'id': review_id},
        {'$set': {
            'response_text': payload.response_text,
            'status': 'responded',
            'responded_at': _now().isoformat(),
            'updated_at': _now(),
        }}
    )
    refreshed = await db.dewi_toko_reviews.find_one({'id': review_id})
    if refreshed:
        await _mirror_review(db, refreshed)
    return {'message': 'Respons disimpan'}


@router.put('/reviews/{review_id}/flag', deprecated=True)
async def flag_review(review_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_toko_reviews.find_one({'id': review_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Review tidak ditemukan')
    await db.dewi_toko_reviews.update_one(
        {'id': review_id},
        {'$set': {'status': 'flagged', 'updated_at': _now()}}
    )
    refreshed = await db.dewi_toko_reviews.find_one({'id': review_id})
    if refreshed:
        await _mirror_review(db, refreshed)
    return {'message': 'Review diflag'}


@router.delete('/reviews/{review_id}', deprecated=True)
async def delete_review(review_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_toko_reviews.find_one({'id': review_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Review tidak ditemukan')
    await db.dewi_toko_reviews.delete_one({'id': review_id})
    return {'message': 'Review dihapus'}
