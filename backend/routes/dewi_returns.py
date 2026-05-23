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
from routes._toko_adapter import (
    toko_return_to_marketing, marketing_return_to_toko,
    toko_review_to_marketing, marketing_review_to_toko,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/dewi/toko', tags=['Dewi-Toko-CS'])


# ── P1.D cleanup: SSOT is marketing_returns + marketing_reviews ─────────────

class _ScopedShimView:
    """Generic shim that filters _legacy_toko=True, applies forward adapter on
    inserts, and back adapter on reads. Mirrors _ScopedView pattern in dewi_toko.py.
    """
    def __init__(self, coll, to_modern, to_legacy):
        self._c = coll
        self._fwd = to_modern
        self._back = to_legacy

    def _q(self, query=None):
        q = dict(query or {})
        q.setdefault("_legacy_toko", True)
        return q

    async def find_one(self, query=None, *a, **k):
        doc = await self._c.find_one(self._q(query), *a, **k)
        return self._back(doc) if doc else None

    def find(self, query=None, *a, **k):
        cur = self._c.find(self._q(query), *a, **k)
        return _ShimCursor(cur, self._back)

    async def count_documents(self, query=None, *a, **k):
        return await self._c.count_documents(self._q(query), *a, **k)

    async def insert_one(self, doc, **k):
        return await self._c.insert_one(self._fwd(doc), **k)

    async def update_one(self, query, update, **k):
        return await self._c.update_one(self._q(query), update, **k)

    async def delete_one(self, query, **k):
        return await self._c.delete_one(self._q(query), **k)


class _ShimCursor:
    def __init__(self, cur, back):
        self._cur = cur
        self._back = back

    def sort(self, *a, **k):
        self._cur = self._cur.sort(*a, **k); return self

    def skip(self, n):
        self._cur = self._cur.skip(n); return self

    def limit(self, n):
        self._cur = self._cur.limit(n); return self

    async def to_list(self, length=None):
        docs = await self._cur.to_list(length=length)
        return [self._back(d) for d in docs]


def _lr(db):
    return _ScopedShimView(db.marketing_returns, toko_return_to_marketing, marketing_return_to_toko)


def _lrv(db):
    return _ScopedShimView(db.marketing_reviews, toko_review_to_marketing, marketing_review_to_toko)



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
    items = await _lr(db).find(filt).sort('created_at', -1).to_list(length=limit)
    return _clean_list(items)


@router.get('/returns/summary', deprecated=True)
async def returns_summary(user=Depends(require_auth)):
    db = get_db()
    new_count = await _lr(db).count_documents({'status': 'new'})
    investigating = await _lr(db).count_documents({'status': 'investigating'})
    resolved = await _lr(db).count_documents({'status': {'$in': ['resolved', 'closed']}})
    low_reviews = await _lrv(db).count_documents({'rating': {'$lte': 3}, 'status': {'$in': ['unread', 'flagged']}})
    return {
        'new_returns': new_count,
        'investigating': investigating,
        'resolved': resolved,
        'low_reviews': low_reviews,
    }


@router.get('/returns/{return_id}', deprecated=True)
async def get_return(return_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await _lr(db).find_one({'id': return_id})
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
    await _lr(db).insert_one(doc)
    return {'message': 'Kasus return dibuat', 'id': doc['id'], 'return_code': code}


@router.put('/returns/{return_id}', deprecated=True)
async def update_return(return_id: str, payload: ReturnPatchIn, user=Depends(require_auth)):
    db = get_db()
    doc = await _lr(db).find_one({'id': return_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Return tidak ditemukan')
    patch = payload.model_dump(exclude_none=True)
    if not patch:
        raise HTTPException(status_code=422, detail='Tidak ada field yang diupdate')
    patch['updated_at'] = _now()
    await _lr(db).update_one({'id': return_id}, {'$set': patch})
    return {'message': 'Return diperbarui'}


@router.post('/returns/{return_id}/decision', deprecated=True)
async def make_return_decision(return_id: str, payload: ReturnDecisionIn, user=Depends(require_auth)):
    db = get_db()
    doc = await _lr(db).find_one({'id': return_id})
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
    await _lr(db).update_one({'id': return_id}, {'$set': patch})
    return {'message': f'Keputusan: {payload.decision}'}


@router.delete('/returns/{return_id}', deprecated=True)
async def delete_return(return_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await _lr(db).find_one({'id': return_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Return tidak ditemukan')
    await _lr(db).delete_one({'id': return_id})
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
    items = await _lrv(db).find(filt).sort('created_at', -1).to_list(length=limit)
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
    await _lrv(db).insert_one(doc)
    return {'message': 'Review dicatat', 'id': doc['id']}


@router.put('/reviews/{review_id}/respond', deprecated=True)
async def respond_review(review_id: str, payload: ReviewResponseIn, user=Depends(require_auth)):
    db = get_db()
    doc = await _lrv(db).find_one({'id': review_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Review tidak ditemukan')
    await _lrv(db).update_one(
        {'id': review_id},
        {'$set': {
            'response_text': payload.response_text,
            'status': 'responded',
            'responded_at': _now().isoformat(),
            'updated_at': _now(),
        }}
    )
    return {'message': 'Respons disimpan'}


@router.put('/reviews/{review_id}/flag', deprecated=True)
async def flag_review(review_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await _lrv(db).find_one({'id': review_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Review tidak ditemukan')
    await _lrv(db).update_one(
        {'id': review_id},
        {'$set': {'status': 'flagged', 'updated_at': _now()}}
    )
    return {'message': 'Review diflag'}


@router.delete('/reviews/{review_id}', deprecated=True)
async def delete_review(review_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await _lrv(db).find_one({'id': review_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Review tidak ditemukan')
    await _lrv(db).delete_one({'id': review_id})
    return {'message': 'Review dihapus'}
