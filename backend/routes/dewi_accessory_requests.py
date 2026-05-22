"""Session 27 — GAP-R3 Accessory Request Workflow
RnD → Admin Aksesoris untuk request aksesoris sebelum sample production.

Status workflow:
  draft → submitted → allocated → delivered (or rejected/cancelled)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db
from auth import require_auth
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import re

router = APIRouter(prefix="/api/dewi/accessory-requests", tags=["RnD-Accessory-Requests"])


def now_utc():
    return datetime.now(timezone.utc)


def sid():
    return str(uuid.uuid4())


def serialize(doc):
    if doc is None:
        return None
    doc = dict(doc)
    doc.pop('_id', None)
    for k, v in doc.items():
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


VALID_STATUSES = {'draft', 'submitted', 'allocated', 'delivered', 'rejected', 'cancelled'}


# ─── LIST ────────────────────────────────────────────────────────────────────
@router.get('')
async def list_requests(
    status:            Optional[str] = None,
    sample_request_id: Optional[str] = None,
    style_id:          Optional[str] = None,
    urgent_only:       Optional[bool] = False,
    search:            Optional[str] = None,
    limit:             int = 200,
    user: dict = Depends(require_auth),
):
    db = get_db()
    q: dict = {}
    if status:
        q['status'] = status
    if sample_request_id:
        q['sample_request_id'] = sample_request_id
    if style_id:
        q['style_id'] = style_id
    if urgent_only:
        q['urgent'] = True
    if search:
        rx = re.escape(search)
        q['$or'] = [
            {'request_code': {'$regex': rx, '$options': 'i'}},
            {'style_code':   {'$regex': rx, '$options': 'i'}},
            {'style_name':   {'$regex': rx, '$options': 'i'}},
            {'requester_name': {'$regex': rx, '$options': 'i'}},
        ]
    items = await db.dewi_accessory_requests.find(q).sort('created_at', -1).limit(limit).to_list(length=limit)
    return [serialize(it) for it in items]


# ─── DETAIL ──────────────────────────────────────────────────────────────────
@router.get('/{request_id}')
async def get_request(request_id: str, user: dict = Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_accessory_requests.find_one({'id': request_id})
    if not doc:
        raise HTTPException(404, 'Request tidak ditemukan')
    return serialize(doc)


# ─── CREATE ──────────────────────────────────────────────────────────────────
@router.post('')
async def create_request(body: dict, user: dict = Depends(require_auth)):
    db = get_db()

    items = body.get('items') or []
    if not items:
        raise HTTPException(400, 'Minimal 1 item aksesoris harus diisi')

    sample_id = body.get('sample_request_id') or ''
    style_id  = body.get('style_id') or ''

    style_code = body.get('style_code') or ''
    style_name = body.get('style_name') or ''

    # Auto-resolve style info if not provided
    if style_id and not (style_code and style_name):
        st = await db.dewi_rnd_styles.find_one({'id': style_id})
        if st:
            style_code = style_code or st.get('style_code', '')
            style_name = style_name or st.get('style_name', '')

    # Generate code
    today = now_utc().strftime('%y%m%d')
    seq = await db.dewi_accessory_requests.count_documents({'request_code': {'$regex': f'^REQ-AKS-{today}-'}})
    code = body.get('request_code') or f'REQ-AKS-{today}-{seq+1:03d}'

    doc = {
        'id': sid(),
        'request_code': code,
        'sample_request_id': sample_id,
        'style_id': style_id,
        'style_code': style_code,
        'style_name': style_name,
        'items': [
            {
                'material_code': it.get('material_code', ''),
                'material_name': it.get('material_name', ''),
                'qty': float(it.get('qty', 0) or 0),
                'unit': it.get('unit', 'pcs'),
                'notes': it.get('notes', ''),
            } for it in items
        ],
        'urgent': bool(body.get('urgent', False)),
        'needed_by_date': body.get('needed_by_date', ''),
        'notes': body.get('notes', ''),
        'status': body.get('status', 'draft'),
        'requester_id': user['id'],
        'requester_name': user.get('name', ''),
        'allocated_by': None,
        'allocated_at': None,
        'delivered_by': None,
        'delivered_at': None,
        'rejection_reason': None,
        'created_at': now_utc(),
        'updated_at': now_utc(),
    }
    await db.dewi_accessory_requests.insert_one(doc)
    return serialize(doc)


# ─── UPDATE (edit details — only if still draft/submitted) ───────────────────
@router.put('/{request_id}')
async def update_request(request_id: str, body: dict, user: dict = Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_accessory_requests.find_one({'id': request_id})
    if not doc:
        raise HTTPException(404, 'Request tidak ditemukan')
    if doc['status'] in ('delivered', 'rejected', 'cancelled'):
        raise HTTPException(400, f"Tidak bisa edit request dengan status {doc['status']}")

    upd = {k: v for k, v in body.items() if k not in ('id', '_id', 'created_at', 'created_by', 'requester_id', 'request_code')}
    if 'items' in upd:
        upd['items'] = [
            {
                'material_code': it.get('material_code', ''),
                'material_name': it.get('material_name', ''),
                'qty': float(it.get('qty', 0) or 0),
                'unit': it.get('unit', 'pcs'),
                'notes': it.get('notes', ''),
            } for it in (upd['items'] or [])
        ]
    upd['updated_at'] = now_utc()
    await db.dewi_accessory_requests.update_one({'id': request_id}, {'$set': upd})
    return {'ok': True}


# ─── SUBMIT (draft → submitted) ──────────────────────────────────────────────
@router.post('/{request_id}/submit')
async def submit_request(request_id: str, user: dict = Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_accessory_requests.find_one({'id': request_id})
    if not doc:
        raise HTTPException(404, 'Request tidak ditemukan')
    if doc['status'] != 'draft':
        raise HTTPException(400, 'Hanya request berstatus draft yang bisa disubmit')
    await db.dewi_accessory_requests.update_one(
        {'id': request_id},
        {'$set': {
            'status': 'submitted',
            'submitted_at': now_utc(),
            'updated_at': now_utc(),
        }}
    )
    return {'ok': True}


# ─── ALLOCATE (submitted → allocated, by Admin Aksesoris) ────────────────────
@router.post('/{request_id}/allocate')
async def allocate_request(request_id: str, body: dict = None, user: dict = Depends(require_auth)):
    db = get_db()
    body = body or {}
    doc = await db.dewi_accessory_requests.find_one({'id': request_id})
    if not doc:
        raise HTTPException(404, 'Request tidak ditemukan')
    if doc['status'] != 'submitted':
        raise HTTPException(400, 'Hanya request berstatus submitted yang bisa di-allocate')
    await db.dewi_accessory_requests.update_one(
        {'id': request_id},
        {'$set': {
            'status': 'allocated',
            'allocated_by': user.get('name', ''),
            'allocated_at': now_utc(),
            'allocation_notes': body.get('notes', ''),
            'updated_at': now_utc(),
        }}
    )
    return {'ok': True}


# ─── DELIVER (allocated → delivered) ─────────────────────────────────────────
@router.post('/{request_id}/deliver')
async def deliver_request(request_id: str, body: dict = None, user: dict = Depends(require_auth)):
    db = get_db()
    body = body or {}
    doc = await db.dewi_accessory_requests.find_one({'id': request_id})
    if not doc:
        raise HTTPException(404, 'Request tidak ditemukan')
    if doc['status'] != 'allocated':
        raise HTTPException(400, 'Hanya request berstatus allocated yang bisa di-deliver')
    await db.dewi_accessory_requests.update_one(
        {'id': request_id},
        {'$set': {
            'status': 'delivered',
            'delivered_by': user.get('name', ''),
            'delivered_at': now_utc(),
            'delivery_notes': body.get('notes', ''),
            'updated_at': now_utc(),
        }}
    )
    return {'ok': True}


# ─── REJECT ──────────────────────────────────────────────────────────────────
@router.post('/{request_id}/reject')
async def reject_request(request_id: str, body: dict = None, user: dict = Depends(require_auth)):
    db = get_db()
    body = body or {}
    doc = await db.dewi_accessory_requests.find_one({'id': request_id})
    if not doc:
        raise HTTPException(404, 'Request tidak ditemukan')
    if doc['status'] in ('delivered', 'cancelled'):
        raise HTTPException(400, f"Tidak bisa reject request dengan status {doc['status']}")
    await db.dewi_accessory_requests.update_one(
        {'id': request_id},
        {'$set': {
            'status': 'rejected',
            'rejection_reason': body.get('reason', ''),
            'rejected_by': user.get('name', ''),
            'rejected_at': now_utc(),
            'updated_at': now_utc(),
        }}
    )
    return {'ok': True}


# ─── DELETE ──────────────────────────────────────────────────────────────────
@router.delete('/{request_id}')
async def delete_request(request_id: str, user: dict = Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_accessory_requests.find_one({'id': request_id})
    if not doc:
        raise HTTPException(404, 'Request tidak ditemukan')
    if doc['status'] not in ('draft', 'rejected', 'cancelled'):
        raise HTTPException(400, 'Hanya request berstatus draft/rejected/cancelled yang bisa dihapus')
    await db.dewi_accessory_requests.delete_one({'id': request_id})
    return {'ok': True}


# ─── STATS / DASHBOARD ───────────────────────────────────────────────────────
@router.get('/stats/summary')
async def stats_summary(user: dict = Depends(require_auth)):
    db = get_db()
    pipeline = [
        {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
    ]
    by_status = {row['_id']: row['count'] async for row in db.dewi_accessory_requests.aggregate(pipeline)}
    total = sum(by_status.values())
    urgent_pending = await db.dewi_accessory_requests.count_documents({
        'urgent': True,
        'status': {'$in': ['submitted', 'allocated']}
    })
    return {
        'total': total,
        'draft': by_status.get('draft', 0),
        'submitted': by_status.get('submitted', 0),
        'allocated': by_status.get('allocated', 0),
        'delivered': by_status.get('delivered', 0),
        'rejected': by_status.get('rejected', 0),
        'cancelled': by_status.get('cancelled', 0),
        'urgent_pending': urgent_pending,
    }
