"""
CV. Dewi Aditya — Phase 5B: Online Orders Management
  - Order ingestion (manual + mock sync from channels)
  - Order lifecycle: new → packed → shipped → delivered → closed
  - Packing batches (3x/day schedule)
  - Shipping info: courier, tracking, timestamps

Collections:
- dewi_toko_orders
- dewi_toko_pack_batches
"""
import re
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from database import get_db
from auth import require_auth
from utils.helpers import _uid, _now, _clean, _clean_list, _next_code

router = APIRouter(prefix='/api/dewi/toko', tags=['Dewi-Toko-Orders'])

ORDER_STATUSES = ['new', 'packed', 'shipped', 'delivered', 'closed', 'cancelled']
CHANNEL_CODES = ['shopee', 'tokopedia', 'tiktok_shop', 'website', 'manual']
SCHEDULE_TIMES = ['08:00', '13:00', '15:00']
COURIERS = ['JNE', 'J&T', 'SiCepat', 'AnterAja', 'Gosend', 'Grab', 'Lainnya']

# ── Models ────────────────────────────────────────────────────────────────────

class OrderItem(BaseModel):
    sku_code: str
    product_name: Optional[str] = None
    qty: int = Field(default=1, ge=1)
    price: float = Field(default=0.0, ge=0)

class OrderIn(BaseModel):
    channel_code: str = 'manual'
    order_ref: Optional[str] = None  # marketplace order number
    customer_name: str = Field(..., min_length=1)
    customer_address: Optional[str] = None
    customer_city: Optional[str] = None
    customer_phone: Optional[str] = None
    items: List[OrderItem] = Field(default_factory=list)
    total_amount: float = Field(default=0.0, ge=0)
    fee_amount: float = Field(default=0.0, ge=0)
    courier: Optional[str] = None
    notes: Optional[str] = None

class OrderPatchIn(BaseModel):
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    customer_city: Optional[str] = None
    customer_phone: Optional[str] = None
    items: Optional[List[OrderItem]] = None
    total_amount: Optional[float] = Field(default=None, ge=0)
    fee_amount: Optional[float] = Field(default=None, ge=0)
    courier: Optional[str] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None

class OrderStatusIn(BaseModel):
    status: str
    tracking_number: Optional[str] = None
    notes: Optional[str] = None

class PackBatchIn(BaseModel):
    batch_name: Optional[str] = None
    schedule_time: str = '13:00'
    order_ids: List[str] = Field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_order_or_404(db, order_id: str):
    doc = await db.dewi_toko_orders.find_one({'id': order_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Order tidak ditemukan')
    return doc


# ── ORDERS ────────────────────────────────────────────────────────────────────

@router.get('/orders')
async def list_orders(
    status: Optional[str] = None,
    channel_code: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    user=Depends(require_auth)
):
    db = get_db()
    filt: dict = {}
    if status:
        filt['status'] = status
    if channel_code:
        filt['channel_code'] = channel_code
    if search:
        filt['$or'] = [
            {'customer_name': {'$regex': re.escape(search), '$options': 'i'}},
            {'order_number': {'$regex': re.escape(search), '$options': 'i'}},
            {'order_ref': {'$regex': re.escape(search), '$options': 'i'}},
        ]
    items = await db.dewi_toko_orders.find(filt).sort('created_at', -1).to_list(length=limit)
    return _clean_list(items)


@router.get('/orders/summary')
async def orders_summary(user=Depends(require_auth)):
    db = get_db()
    new_count = await db.dewi_toko_orders.count_documents({'status': 'new'})
    packed_count = await db.dewi_toko_orders.count_documents({'status': 'packed'})
    shipped_count = await db.dewi_toko_orders.count_documents({'status': 'shipped'})
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    delivered_today = await db.dewi_toko_orders.count_documents(
        {'status': 'delivered', 'updated_at': {'$gte': datetime.fromisoformat(today_str + 'T00:00:00+00:00')}}
    )
    total_today = await db.dewi_toko_orders.count_documents(
        {'created_at': {'$gte': datetime.fromisoformat(today_str + 'T00:00:00+00:00')}}
    )
    return {
        'new': new_count,
        'packed': packed_count,
        'shipped': shipped_count,
        'delivered_today': delivered_today,
        'total_today': total_today,
    }


@router.get('/orders/{order_id}')
async def get_order(order_id: str, user=Depends(require_auth)):
    db = get_db()
    return _clean(await _get_order_or_404(db, order_id))


@router.post('/orders', status_code=201)
async def create_order(payload: OrderIn, user=Depends(require_auth)):
    db = get_db()
    code = await _next_code(db, 'ORD', 'dewi_toko_orders', 'order_number')
    net = payload.total_amount - payload.fee_amount
    doc = {
        'id': _uid(),
        'order_number': code,
        'order_ref': payload.order_ref,
        'channel_code': payload.channel_code,
        'customer_name': payload.customer_name,
        'customer_address': payload.customer_address,
        'customer_city': payload.customer_city,
        'customer_phone': payload.customer_phone,
        'items': [i.model_dump() for i in payload.items],
        'total_amount': payload.total_amount,
        'fee_amount': payload.fee_amount,
        'net_amount': net,
        'status': 'new',
        'courier': payload.courier,
        'tracking_number': None,
        'notes': payload.notes,
        'pack_batch_id': None,
        'packed_at': None,
        'shipped_at': None,
        'created_by': user.get('id'),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.dewi_toko_orders.insert_one(doc)
    return {'message': 'Order dibuat', 'id': doc['id'], 'order_number': code}


@router.put('/orders/{order_id}')
async def update_order(order_id: str, payload: OrderPatchIn, user=Depends(require_auth)):
    db = get_db()
    doc = await _get_order_or_404(db, order_id)
    if doc['status'] in ['cancelled', 'closed']:
        raise HTTPException(status_code=400, detail='Order sudah ditutup/dibatalkan, tidak bisa diedit')
    patch = payload.model_dump(exclude_none=True)
    if 'items' in patch:
        patch['items'] = [i.model_dump() if hasattr(i, 'model_dump') else i for i in patch['items']]
    if 'total_amount' in patch or 'fee_amount' in patch:
        ta = patch.get('total_amount', doc.get('total_amount', 0))
        fa = patch.get('fee_amount', doc.get('fee_amount', 0))
        patch['net_amount'] = ta - fa
    if not patch:
        raise HTTPException(status_code=422, detail='Tidak ada field yang diupdate')
    patch['updated_at'] = _now()
    await db.dewi_toko_orders.update_one({'id': order_id}, {'$set': patch})
    return {'message': 'Order diperbarui'}


@router.post('/orders/{order_id}/status')
async def update_order_status(order_id: str, payload: OrderStatusIn, user=Depends(require_auth)):
    db = get_db()
    doc = await _get_order_or_404(db, order_id)
    if payload.status not in ORDER_STATUSES:
        raise HTTPException(status_code=422, detail=f'Status tidak valid: {ORDER_STATUSES}')
    patch: dict = {'status': payload.status, 'updated_at': _now()}
    if payload.tracking_number:
        patch['tracking_number'] = payload.tracking_number
    if payload.notes:
        patch['notes'] = payload.notes
    if payload.status == 'packed':
        patch['packed_at'] = _now().isoformat()
    if payload.status == 'shipped':
        patch['shipped_at'] = _now().isoformat()
    await db.dewi_toko_orders.update_one({'id': order_id}, {'$set': patch})
    return {'message': f'Status diperbarui ke {payload.status}'}


@router.delete('/orders/{order_id}')
async def cancel_order(order_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await _get_order_or_404(db, order_id)
    if doc['status'] not in ['new', 'packed']:
        raise HTTPException(status_code=400, detail='Hanya order berstatus new/packed yang bisa dibatalkan')
    await db.dewi_toko_orders.update_one(
        {'id': order_id},
        {'$set': {'status': 'cancelled', 'updated_at': _now()}}
    )
    return {'message': 'Order dibatalkan'}


# ── PACK BATCHES ──────────────────────────────────────────────────────────────

@router.get('/pack-batches')
async def list_pack_batches(
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(require_auth)
):
    db = get_db()
    filt: dict = {}
    if status:
        filt['status'] = status
    items = await db.dewi_toko_pack_batches.find(filt).sort('created_at', -1).to_list(length=limit)
    return _clean_list(items)


@router.post('/pack-batches', status_code=201)
async def create_pack_batch(payload: PackBatchIn, user=Depends(require_auth)):
    db = get_db()
    if payload.schedule_time not in SCHEDULE_TIMES:
        raise HTTPException(status_code=422, detail=f'Waktu jadwal tidak valid. Pilih: {SCHEDULE_TIMES}')
    # Validate orders exist and are packable — batch fetch
    valid_order_ids = []
    if payload.order_ids:
        async for d in db.dewi_toko_orders.find(
            {'id': {'$in': payload.order_ids}}, {'_id': 0, 'id': 1, 'status': 1}
        ):
            if d.get('status') == 'new':
                valid_order_ids.append(d['id'])
    code = await _next_code(db, 'PACK', 'dewi_toko_pack_batches', 'batch_code')
    name = payload.batch_name or f'Batch Packing {payload.schedule_time}'
    batch_doc = {
        'id': _uid(),
        'batch_code': code,
        'batch_name': name,
        'schedule_time': payload.schedule_time,
        'order_ids': valid_order_ids,
        'total_orders': len(valid_order_ids),
        'status': 'open',
        'created_by': user.get('id'),
        'created_at': _now(),
        'closed_at': None,
    }
    await db.dewi_toko_pack_batches.insert_one(batch_doc)
    # Mark orders as packed
    if valid_order_ids:
        await db.dewi_toko_orders.update_many(
            {'id': {'$in': valid_order_ids}},
            {'$set': {'status': 'packed', 'pack_batch_id': batch_doc['id'], 'packed_at': _now().isoformat(), 'updated_at': _now()}}
        )
    return {'message': f'Batch packing dibuat dengan {len(valid_order_ids)} order', 'id': batch_doc['id'], 'batch_code': code}


@router.post('/pack-batches/{batch_id}/close')
async def close_pack_batch(batch_id: str, user=Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_toko_pack_batches.find_one({'id': batch_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Batch tidak ditemukan')
    if doc['status'] == 'closed':
        raise HTTPException(status_code=400, detail='Batch sudah ditutup')
    await db.dewi_toko_pack_batches.update_one(
        {'id': batch_id},
        {'$set': {'status': 'closed', 'closed_at': _now().isoformat()}}
    )
    return {'message': 'Batch ditutup'}
