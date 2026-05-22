"""Phase 7 — RnD & Style Master
Modul: Style Master, Sample Requests, Revisions, Material Research, Sample Costing
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from motor.motor_asyncio import AsyncIOMotorDatabase
from database import get_db
from auth import require_auth
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import uuid
import os
import shutil
import re

router = APIRouter(prefix="/api/dewi/rnd", tags=["RnD"])

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

# ──────────────────────────────────────────────────────────────────────────────
# STYLE MASTER (Master Style & Tech Pack)
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/styles')
async def list_styles(
    search: Optional[str] = None,
    category: Optional[str] = None,
    buyer: Optional[str] = None,
    season: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
    user: dict = Depends(require_auth),
):
    """List all styles with filters"""
    db = get_db()
    q = {}
    if search:
        q['$or'] = [
            {'style_code': {'$regex': re.escape(search), '$options': 'i'}},
            {'style_name': {'$regex': re.escape(search), '$options': 'i'}},
        ]
    if category:
        q['category'] = category
    if buyer:
        q['buyer'] = buyer
    if season:
        q['season'] = season
    if status:
        q['status'] = status
    
    items = await db.dewi_rnd_styles.find(q).sort('created_at', -1).limit(limit).to_list(length=limit)
    return [serialize(it) for it in items]


@router.get('/styles/pending-review')
async def list_styles_pending_review_top(user: dict = Depends(require_auth)):
    """List all styles currently pending Owner review. (MUST be before /{style_id} route)"""
    db = get_db()
    items = await db.dewi_rnd_styles.find(
        {'status': 'pending_owner_review'}
    ).sort('submitted_for_review_at', 1).to_list(200)
    return [serialize(it) for it in items]

@router.post('/styles')
async def create_style(body: dict, user: dict = Depends(require_auth)):
    """Create new style"""
    db = get_db()
    code = (body.get('style_code') or '').strip().upper()
    name = (body.get('style_name') or '').strip()
    
    if not code or not name:
        raise HTTPException(400, 'style_code dan style_name wajib diisi')
    
    # Check duplicate
    existing = await db.dewi_rnd_styles.find_one({'style_code': code})
    if existing:
        raise HTTPException(409, f'Style code {code} sudah ada')
    
    doc = {
        'id': sid(),
        'style_code': code,
        'style_name': name,
        'category': body.get('category', ''),
        'buyer': body.get('buyer', ''),
        'fabric_type': body.get('fabric_type', ''),
        'season': body.get('season', ''),
        'description': body.get('description', ''),
        'status': body.get('status', 'draft'),
        # ── Production-Maklon Overhaul: RnD Type separation ──────────────────
        'rnd_type': body.get('rnd_type', 'internal_product'),  # internal_product | maklon_product
        'client_id': body.get('client_id', None),   # FK ke dewi_maklon_clients (untuk maklon_product)
        'client_name': body.get('client_name', ''),
        'promoted_to_model_id': None,  # set saat style di-promote ke rahaza_models
        # ─────────────────────────────────────────────────────────────────────
        'techpack_url': None,
        'techpack_name': None,
        'design_images': [],
        'variants': [],
        'created_by': user['id'],
        'created_by_name': user.get('name', ''),
        'created_at': now_utc(),
        'updated_at': now_utc(),
    }
    await db.dewi_rnd_styles.insert_one(doc)
    return serialize(doc)

@router.get('/styles/{style_id}')
async def get_style(style_id: str, user: dict = Depends(require_auth)):
    """Get style by ID"""
    db = get_db()
    s = await db.dewi_rnd_styles.find_one({'id': style_id})
    if not s:
        raise HTTPException(404, 'Style tidak ditemukan')
    return serialize(s)

@router.put('/styles/{style_id}')
async def update_style(style_id: str, body: dict, user: dict = Depends(require_auth)):
    """Update style"""
    db = get_db()
    body.pop('_id', None)
    body.pop('id', None)
    body.pop('created_at', None)
    body.pop('created_by', None)
    body['updated_at'] = now_utc()
    
    if 'style_code' in body:
        body['style_code'] = body['style_code'].strip().upper()
    
    res = await db.dewi_rnd_styles.update_one({'id': style_id}, {'$set': body})
    if res.matched_count == 0:
        raise HTTPException(404, 'Style tidak ditemukan')
    
    updated = await db.dewi_rnd_styles.find_one({'id': style_id})
    return serialize(updated)

@router.delete('/styles/{style_id}')
async def delete_style(style_id: str, user: dict = Depends(require_auth)):
    """Delete style"""
    db = get_db()
    res = await db.dewi_rnd_styles.delete_one({'id': style_id})
    if res.deleted_count == 0:
        raise HTTPException(404, 'Style tidak ditemukan')
    return {'success': True}


# ── GAP-R2: Design Selection Approval Workflow ────────────────────────────────

@router.post('/styles/{style_id}/submit-for-review')
async def submit_style_for_review(style_id: str, body: dict = {}, user: dict = Depends(require_auth)):
    """RnD staff submits style for Owner review.
    Transitions: draft | active → pending_owner_review
    """
    db = get_db()
    style = await db.dewi_rnd_styles.find_one({'id': style_id})
    if not style:
        raise HTTPException(404, 'Style tidak ditemukan')
    if style.get('status') not in ('draft', 'active'):
        raise HTTPException(400, f"Hanya style berstatus draft/active yang bisa diajukan review (saat ini: {style.get('status')})")
    
    now = now_utc()
    await db.dewi_rnd_styles.update_one(
        {'id': style_id},
        {'$set': {
            'status': 'pending_owner_review',
            'submitted_for_review_by': user.get('name', ''),
            'submitted_for_review_by_id': user.get('id', ''),
            'submitted_for_review_at': now,
            'review_notes': body.get('notes', ''),
            'owner_review_result': None,
            'owner_reviewed_by': None,
            'owner_reviewed_at': None,
            'owner_review_notes': None,
            'updated_at': now,
        }}
    )
    updated = await db.dewi_rnd_styles.find_one({'id': style_id})
    return serialize(updated)


@router.post('/styles/{style_id}/owner-approve')
async def owner_approve_style(style_id: str, body: dict = {}, user: dict = Depends(require_auth)):
    """Owner/SuperAdmin approves a style design.
    Transitions: pending_owner_review → approved_for_launch
    """
    db = get_db()
    style = await db.dewi_rnd_styles.find_one({'id': style_id})
    if not style:
        raise HTTPException(404, 'Style tidak ditemukan')
    if style.get('status') != 'pending_owner_review':
        raise HTTPException(400, f"Style harus berstatus pending_owner_review untuk disetujui (saat ini: {style.get('status')})")
    
    now = now_utc()
    await db.dewi_rnd_styles.update_one(
        {'id': style_id},
        {'$set': {
            'status': 'approved_for_launch',
            'owner_review_result': 'approved',
            'owner_reviewed_by': user.get('name', ''),
            'owner_reviewed_by_id': user.get('id', ''),
            'owner_reviewed_at': now,
            'owner_review_notes': body.get('notes', ''),
            'updated_at': now,
        }}
    )
    updated = await db.dewi_rnd_styles.find_one({'id': style_id})
    return serialize(updated)


@router.post('/styles/{style_id}/promote-to-production')
async def promote_style_to_production(style_id: str, body: dict = {}, user: dict = Depends(require_auth)):
    """
    Promote approved RnD Internal Style ke Production Model (rahaza_models).
    Hanya berlaku untuk rnd_type = 'internal_product' yang sudah approved_for_launch.
    Juga sync BOM jika ada.
    """
    db = get_db()
    style = await db.dewi_rnd_styles.find_one({'id': style_id})
    if not style:
        raise HTTPException(404, 'Style tidak ditemukan')
    if style.get('rnd_type') == 'maklon_product':
        raise HTTPException(400, 'Style maklon tidak di-promote ke Production Model (produk milik buyer)')
    if style.get('status') != 'approved_for_launch':
        raise HTTPException(400, f"Style harus berstatus approved_for_launch untuk di-promote (saat ini: {style.get('status')})")
    if style.get('promoted_to_model_id'):
        raise HTTPException(400, 'Style sudah pernah di-promote ke Production Model')

    import uuid
    model_id = str(uuid.uuid4())
    model_code = body.get('model_code') or style['style_code']
    model_doc = {
        'id': model_id,
        'code': model_code,
        'name': style['style_name'],
        'category': style.get('category', ''),
        'fabric_type': style.get('fabric_type', ''),
        'description': style.get('description', ''),
        'rnd_style_id': style_id,
        'rnd_style_code': style['style_code'],
        'status': 'active',
        'created_by': user['id'],
        'created_by_name': user.get('name', ''),
        'created_at': now_utc(),
        'updated_at': now_utc(),
    }
    await db.rahaza_models.insert_one(model_doc)
    # Mark style as promoted
    await db.dewi_rnd_styles.update_one(
        {'id': style_id},
        {'$set': {
            'promoted_to_model_id': model_id,
            'promoted_at': now_utc(),
            'promoted_by': user['id'],
            'updated_at': now_utc(),
        }}
    )
    return {
        'status': 'promoted',
        'model_id': model_id,
        'model_code': model_code,
        'message': f'Style {style["style_code"]} berhasil di-promote ke Production Model {model_code}',
    }


@router.post('/styles/{style_id}/owner-reject')
async def owner_reject_style(style_id: str, body: dict = {}, user: dict = Depends(require_auth)):
    """Owner/SuperAdmin rejects a style design, sends it back to draft.
    Transitions: pending_owner_review → draft
    """
    db = get_db()
    style = await db.dewi_rnd_styles.find_one({'id': style_id})
    if not style:
        raise HTTPException(404, 'Style tidak ditemukan')
    if style.get('status') != 'pending_owner_review':
        raise HTTPException(400, f"Style harus berstatus pending_owner_review untuk ditolak (saat ini: {style.get('status')})")
    
    if not body.get('notes'):
        raise HTTPException(400, 'Catatan penolakan wajib diisi')
    
    now = now_utc()
    await db.dewi_rnd_styles.update_one(
        {'id': style_id},
        {'$set': {
            'status': 'draft',
            'owner_review_result': 'rejected',
            'owner_reviewed_by': user.get('name', ''),
            'owner_reviewed_by_id': user.get('id', ''),
            'owner_reviewed_at': now,
            'owner_review_notes': body.get('notes', ''),
            'updated_at': now,
        }}
    )
    updated = await db.dewi_rnd_styles.find_one({'id': style_id})
    return serialize(updated)


@router.get('/styles/pending-review-dup-removed')
async def _removed_dup(user: dict = Depends(require_auth)):
    """Placeholder — actual endpoint is at top of file before /{style_id}"""
    return []

# ──────────────────────────────────────────────────────────────────────────────
# SAMPLE REQUESTS (Sample Request & Approval)
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/sample-requests')
async def list_sample_requests(
    style_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
    user: dict = Depends(require_auth),
):
    """List sample requests"""
    db = get_db()
    q = {}
    if style_id:
        q['style_id'] = style_id
    if status:
        q['status'] = status
    
    items = await db.dewi_rnd_sample_requests.find(q).sort('created_at', -1).limit(limit).to_list(length=limit)
    return [serialize(it) for it in items]

@router.post('/sample-requests')
async def create_sample_request(body: dict, user: dict = Depends(require_auth)):
    """Create new sample request"""
    db = get_db()
    style_id = body.get('style_id')
    
    if not style_id:
        raise HTTPException(400, 'style_id wajib diisi')
    
    # Verify style exists
    style = await db.dewi_rnd_styles.find_one({'id': style_id})
    if not style:
        raise HTTPException(404, 'Style tidak ditemukan')
    
    doc = {
        'id': sid(),
        'sample_code': f"SR-{datetime.now().strftime('%Y%m%d')}-{sid()[:6].upper()}",
        'style_id': style_id,
        'style_code': style.get('style_code', ''),
        'style_name': style.get('style_name', ''),
        'quantity': body.get('quantity', 1),
        'priority': body.get('priority', 'normal'),
        'due_date': body.get('due_date'),
        'notes': body.get('notes', ''),
        'status': 'draft',
        'approval_status': None,
        'approved_by': None,
        'approved_by_name': None,
        'approved_at': None,
        'approval_notes': None,
        'created_by': user['id'],
        'created_by_name': user.get('name', ''),
        'created_at': now_utc(),
        'updated_at': now_utc(),
    }
    await db.dewi_rnd_sample_requests.insert_one(doc)
    return serialize(doc)

@router.get('/sample-requests/{request_id}')
async def get_sample_request(request_id: str, user: dict = Depends(require_auth)):
    """Get sample request by ID"""
    db = get_db()
    req = await db.dewi_rnd_sample_requests.find_one({'id': request_id})
    if not req:
        raise HTTPException(404, 'Sample request tidak ditemukan')
    return serialize(req)

@router.put('/sample-requests/{request_id}')
async def update_sample_request(request_id: str, body: dict, user: dict = Depends(require_auth)):
    """Update sample request"""
    db = get_db()
    body.pop('_id', None)
    body.pop('id', None)
    body.pop('created_at', None)
    body['updated_at'] = now_utc()
    
    res = await db.dewi_rnd_sample_requests.update_one({'id': request_id}, {'$set': body})
    if res.matched_count == 0:
        raise HTTPException(404, 'Sample request tidak ditemukan')
    
    updated = await db.dewi_rnd_sample_requests.find_one({'id': request_id})
    return serialize(updated)

@router.post('/sample-requests/{request_id}/submit')
async def submit_sample_request(request_id: str, user: dict = Depends(require_auth)):
    """Submit sample request for approval"""
    db = get_db()
    req = await db.dewi_rnd_sample_requests.find_one({'id': request_id})
    if not req:
        raise HTTPException(404, 'Sample request tidak ditemukan')
    
    if req.get('status') != 'draft':
        raise HTTPException(400, 'Hanya draft yang bisa di-submit')
    
    await db.dewi_rnd_sample_requests.update_one(
        {'id': request_id},
        {'$set': {'status': 'submitted', 'updated_at': now_utc()}}
    )
    
    updated = await db.dewi_rnd_sample_requests.find_one({'id': request_id})
    return serialize(updated)

@router.post('/sample-requests/{request_id}/approve')
async def approve_sample_request(request_id: str, body: dict, user: dict = Depends(require_auth)):
    """Approve sample request"""
    db = get_db()
    req = await db.dewi_rnd_sample_requests.find_one({'id': request_id})
    if not req:
        raise HTTPException(404, 'Sample request tidak ditemukan')
    
    if req.get('status') != 'submitted':
        raise HTTPException(400, 'Hanya submitted yang bisa di-approve')
    
    await db.dewi_rnd_sample_requests.update_one(
        {'id': request_id},
        {'$set': {
            'status': 'approved',
            'approval_status': 'approved',
            'approved_by': user['id'],
            'approved_by_name': user.get('name', ''),
            'approved_at': now_utc(),
            'approval_notes': body.get('notes', ''),
            'updated_at': now_utc(),
        }}
    )
    
    updated = await db.dewi_rnd_sample_requests.find_one({'id': request_id})
    return serialize(updated)

@router.post('/sample-requests/{request_id}/reject')
async def reject_sample_request(request_id: str, body: dict, user: dict = Depends(require_auth)):
    """Reject sample request"""
    db = get_db()
    req = await db.dewi_rnd_sample_requests.find_one({'id': request_id})
    if not req:
        raise HTTPException(404, 'Sample request tidak ditemukan')
    
    if req.get('status') != 'submitted':
        raise HTTPException(400, 'Hanya submitted yang bisa di-reject')
    
    await db.dewi_rnd_sample_requests.update_one(
        {'id': request_id},
        {'$set': {
            'status': 'rejected',
            'approval_status': 'rejected',
            'approved_by': user['id'],
            'approved_by_name': user.get('name', ''),
            'approved_at': now_utc(),
            'approval_notes': body.get('notes', ''),
            'updated_at': now_utc(),
        }}
    )
    
    updated = await db.dewi_rnd_sample_requests.find_one({'id': request_id})
    return serialize(updated)

@router.delete('/sample-requests/{request_id}')
async def delete_sample_request(request_id: str, user: dict = Depends(require_auth)):
    """Delete sample request"""
    db = get_db()
    res = await db.dewi_rnd_sample_requests.delete_one({'id': request_id})
    if res.deleted_count == 0:
        raise HTTPException(404, 'Sample request tidak ditemukan')
    return {'success': True}

# ──────────────────────────────────────────────────────────────────────────────
# REVISIONS (Design Revision Tracking)
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/revisions')
async def list_revisions(
    style_id: Optional[str] = None,
    limit: int = 200,
    user: dict = Depends(require_auth),
):
    """List revisions"""
    db = get_db()
    q = {}
    if style_id:
        q['style_id'] = style_id
    
    items = await db.dewi_rnd_revisions.find(q).sort('created_at', -1).limit(limit).to_list(length=limit)
    return [serialize(it) for it in items]

@router.post('/revisions')
async def create_revision(body: dict, user: dict = Depends(require_auth)):
    """Create new revision"""
    db = get_db()
    style_id = body.get('style_id')
    
    if not style_id:
        raise HTTPException(400, 'style_id wajib diisi')
    
    # Verify style exists
    style = await db.dewi_rnd_styles.find_one({'id': style_id})
    if not style:
        raise HTTPException(404, 'Style tidak ditemukan')
    
    # Get revision number
    prev_revisions = await db.dewi_rnd_revisions.find({'style_id': style_id}).sort('revision_number', -1).to_list(length=1)
    revision_number = 1 if not prev_revisions else prev_revisions[0].get('revision_number', 0) + 1
    
    doc = {
        'id': sid(),
        'style_id': style_id,
        'style_code': style.get('style_code', ''),
        'revision_number': revision_number,
        'revision_name': body.get('revision_name', f'Rev {revision_number}'),
        'changes_summary': body.get('changes_summary', ''),
        'reason': body.get('reason', ''),
        'previous_revision_id': body.get('previous_revision_id'),
        'created_by': user['id'],
        'created_by_name': user.get('name', ''),
        'created_at': now_utc(),
    }
    await db.dewi_rnd_revisions.insert_one(doc)
    return serialize(doc)

@router.get('/revisions/{revision_id}')
async def get_revision(revision_id: str, user: dict = Depends(require_auth)):
    """Get revision by ID"""
    db = get_db()
    rev = await db.dewi_rnd_revisions.find_one({'id': revision_id})
    if not rev:
        raise HTTPException(404, 'Revision tidak ditemukan')
    return serialize(rev)

@router.delete('/revisions/{revision_id}')
async def delete_revision(revision_id: str, user: dict = Depends(require_auth)):
    """Delete revision"""
    db = get_db()
    res = await db.dewi_rnd_revisions.delete_one({'id': revision_id})
    if res.deleted_count == 0:
        raise HTTPException(404, 'Revision tidak ditemukan')
    return {'success': True}

# ──────────────────────────────────────────────────────────────────────────────
# MATERIAL RESEARCH (Fabric/Material Research)
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/materials')
async def list_materials(
    search: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 200,
    user: dict = Depends(require_auth),
):
    """List material research"""
    db = get_db()
    q = {}
    if search:
        q['$or'] = [
            {'material_code': {'$regex': re.escape(search), '$options': 'i'}},
            {'material_name': {'$regex': re.escape(search), '$options': 'i'}},
        ]
    if category:
        q['category'] = category
    
    items = await db.dewi_rnd_materials.find(q).sort('created_at', -1).limit(limit).to_list(length=limit)
    return [serialize(it) for it in items]

@router.post('/materials')
async def create_material(body: dict, user: dict = Depends(require_auth)):
    """Create new material research"""
    db = get_db()
    code = (body.get('material_code') or '').strip().upper()
    name = (body.get('material_name') or '').strip()
    
    if not code or not name:
        raise HTTPException(400, 'material_code dan material_name wajib diisi')
    
    # Check duplicate
    existing = await db.dewi_rnd_materials.find_one({'material_code': code})
    if existing:
        raise HTTPException(409, f'Material code {code} sudah ada')
    
    doc = {
        'id': sid(),
        'material_code': code,
        'material_name': name,
        'category': body.get('category', ''),
        'vendor': body.get('vendor', ''),
        'composition': body.get('composition', ''),
        'weight': body.get('weight', 0),
        'price_per_meter': body.get('price_per_meter', 0),
        'min_order_qty': body.get('min_order_qty', 0),
        'test_results': body.get('test_results', ''),
        'notes': body.get('notes', ''),
        'status': body.get('status', 'active'),
        'created_by': user['id'],
        'created_by_name': user.get('name', ''),
        'created_at': now_utc(),
        'updated_at': now_utc(),
    }
    await db.dewi_rnd_materials.insert_one(doc)
    return serialize(doc)

@router.get('/materials/{material_id}')
async def get_material(material_id: str, user: dict = Depends(require_auth)):
    """Get material by ID"""
    db = get_db()
    mat = await db.dewi_rnd_materials.find_one({'id': material_id})
    if not mat:
        raise HTTPException(404, 'Material tidak ditemukan')
    return serialize(mat)

@router.put('/materials/{material_id}')
async def update_material(material_id: str, body: dict, user: dict = Depends(require_auth)):
    """Update material"""
    db = get_db()
    body.pop('_id', None)
    body.pop('id', None)
    body.pop('created_at', None)
    body['updated_at'] = now_utc()
    
    res = await db.dewi_rnd_materials.update_one({'id': material_id}, {'$set': body})
    if res.matched_count == 0:
        raise HTTPException(404, 'Material tidak ditemukan')
    
    updated = await db.dewi_rnd_materials.find_one({'id': material_id})
    return serialize(updated)

@router.delete('/materials/{material_id}')
async def delete_material(material_id: str, user: dict = Depends(require_auth)):
    """Delete material"""
    db = get_db()
    res = await db.dewi_rnd_materials.delete_one({'id': material_id})
    if res.deleted_count == 0:
        raise HTTPException(404, 'Material tidak ditemukan')
    return {'success': True}

# ──────────────────────────────────────────────────────────────────────────────
# SAMPLE COSTING (Costing & BOM untuk Sample)
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/sample-costing')
async def list_sample_costing(
    sample_request_id: Optional[str] = None,
    limit: int = 200,
    user: dict = Depends(require_auth),
):
    """List sample costing"""
    db = get_db()
    q = {}
    if sample_request_id:
        q['sample_request_id'] = sample_request_id
    
    items = await db.dewi_rnd_sample_costing.find(q).sort('created_at', -1).limit(limit).to_list(length=limit)
    return [serialize(it) for it in items]

@router.post('/sample-costing')
async def create_sample_costing(body: dict, user: dict = Depends(require_auth)):
    """Create new sample costing"""
    db = get_db()
    sample_request_id = body.get('sample_request_id')
    
    if not sample_request_id:
        raise HTTPException(400, 'sample_request_id wajib diisi')
    
    # Verify sample request exists
    req = await db.dewi_rnd_sample_requests.find_one({'id': sample_request_id})
    if not req:
        raise HTTPException(404, 'Sample request tidak ditemukan')
    
    bom_lines = body.get('bom_lines', [])
    total_material_cost = sum(line.get('total_cost', 0) for line in bom_lines)
    
    doc = {
        'id': sid(),
        'sample_request_id': sample_request_id,
        'sample_code': req.get('sample_code', ''),
        'bom_lines': bom_lines,
        'total_material_cost': total_material_cost,
        'labor_cost': body.get('labor_cost', 0),
        'overhead_cost': body.get('overhead_cost', 0),
        'total_cost': total_material_cost + body.get('labor_cost', 0) + body.get('overhead_cost', 0),
        'notes': body.get('notes', ''),
        'created_by': user['id'],
        'created_by_name': user.get('name', ''),
        'created_at': now_utc(),
        'updated_at': now_utc(),
    }
    await db.dewi_rnd_sample_costing.insert_one(doc)
    return serialize(doc)

@router.get('/sample-costing/{costing_id}')
async def get_sample_costing(costing_id: str, user: dict = Depends(require_auth)):
    """Get sample costing by ID"""
    db = get_db()
    costing = await db.dewi_rnd_sample_costing.find_one({'id': costing_id})
    if not costing:
        raise HTTPException(404, 'Sample costing tidak ditemukan')
    return serialize(costing)

@router.put('/sample-costing/{costing_id}')
async def update_sample_costing(costing_id: str, body: dict, user: dict = Depends(require_auth)):
    """Update sample costing"""
    db = get_db()
    body.pop('_id', None)
    body.pop('id', None)
    body.pop('created_at', None)
    body['updated_at'] = now_utc()
    
    # Recalculate totals
    if 'bom_lines' in body:
        total_material_cost = sum(line.get('total_cost', 0) for line in body['bom_lines'])
        body['total_material_cost'] = total_material_cost
        body['total_cost'] = total_material_cost + body.get('labor_cost', 0) + body.get('overhead_cost', 0)
    
    res = await db.dewi_rnd_sample_costing.update_one({'id': costing_id}, {'$set': body})
    if res.matched_count == 0:
        raise HTTPException(404, 'Sample costing tidak ditemukan')
    
    updated = await db.dewi_rnd_sample_costing.find_one({'id': costing_id})
    return serialize(updated)

@router.delete('/sample-costing/{costing_id}')
async def delete_sample_costing(costing_id: str, user: dict = Depends(require_auth)):
    """Delete sample costing"""
    db = get_db()
    res = await db.dewi_rnd_sample_costing.delete_one({'id': costing_id})
    if res.deleted_count == 0:
        raise HTTPException(404, 'Sample costing tidak ditemukan')
    return {'success': True}

# ──────────────────────────────────────────────────────────────────────────────
# DASHBOARD (Portal RnD)
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/dashboard')
async def get_rnd_dashboard(user: dict = Depends(require_auth)):
    """Comprehensive RnD Portal dashboard stats + recent activity"""
    db = get_db()

    total_styles   = await db.dewi_rnd_styles.count_documents({})
    active_styles  = await db.dewi_rnd_styles.count_documents({'status': 'active'})
    draft_styles   = await db.dewi_rnd_styles.count_documents({'status': 'draft'})
    review_styles  = await db.dewi_rnd_styles.count_documents({'status': 'review'})

    total_samples   = await db.dewi_rnd_sample_requests.count_documents({})
    pending_samples = await db.dewi_rnd_sample_requests.count_documents({'status': 'submitted'})
    approved_samples= await db.dewi_rnd_sample_requests.count_documents({'status': 'approved'})
    rejected_samples= await db.dewi_rnd_sample_requests.count_documents({'status': 'rejected'})

    total_materials = await db.dewi_rnd_materials.count_documents({})
    total_revisions = await db.dewi_rnd_revisions.count_documents({})
    total_patterns  = await db.dewi_rnd_patterns.count_documents({})
    total_hpp       = await db.dewi_rnd_hpp.count_documents({})
    total_variants  = await db.dewi_rnd_variants.count_documents({})

    # Recent activity — last 5 samples & styles
    recent_samples = await db.dewi_rnd_sample_requests.find(
        {}, {'_id': 0}
    ).sort('created_at', -1).limit(5).to_list(5)

    recent_styles = await db.dewi_rnd_styles.find(
        {}, {'_id': 0}
    ).sort('created_at', -1).limit(5).to_list(5)

    # Latest HPP records
    recent_hpp = await db.dewi_rnd_hpp.find(
        {}, {'_id': 0}
    ).sort('created_at', -1).limit(5).to_list(5)

    def fmt(docs):
        result = []
        for d in docs:
            d2 = dict(d)
            for k, v in d2.items():
                if isinstance(v, datetime):
                    d2[k] = v.isoformat()
            result.append(d2)
        return result

    return {
        'kpi': {
            'total_styles':    total_styles,
            'active_styles':   active_styles,
            'draft_styles':    draft_styles,
            'review_styles':   review_styles,
            'pending_samples': pending_samples,
            'approved_samples':approved_samples,
            'rejected_samples':rejected_samples,
            'total_samples':   total_samples,
            'total_materials': total_materials,
            'total_revisions': total_revisions,
            'total_patterns':  total_patterns,
            'total_hpp':       total_hpp,
            'total_variants':  total_variants,
        },
        'recent_samples': fmt(recent_samples),
        'recent_styles':  fmt(recent_styles),
        'recent_hpp':     fmt(recent_hpp),
    }


# ──────────────────────────────────────────────────────────────────────────────
# VARIANTS (Color × Size per Style)
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/variants')
async def list_variants(
    style_id: Optional[str] = None,
    user: dict = Depends(require_auth),
):
    db = get_db()
    q = {}
    if style_id:
        q['style_id'] = style_id
    docs = await db.dewi_rnd_variants.find(q, {'_id': 0}).sort('created_at', -1).to_list(500)
    return [serialize(d) for d in docs]


@router.post('/variants')
async def create_variant(body: dict, user: dict = Depends(require_auth)):
    db = get_db()
    doc = {
        'id':         sid(),
        'style_id':   body.get('style_id', ''),
        'style_code': body.get('style_code', ''),
        'style_name': body.get('style_name', ''),
        'color':      body.get('color', ''),
        'color_code': body.get('color_code', ''),
        'sizes':      body.get('sizes', []),   # list of {size, sku, qty_plan}
        'status':     body.get('status', 'active'),
        'notes':      body.get('notes', ''),
        'created_by':      user['id'],
        'created_by_name': user.get('name', ''),
        'created_at': now_utc(),
        'updated_at': now_utc(),
    }
    await db.dewi_rnd_variants.insert_one(doc)
    return serialize(doc)


@router.put('/variants/{variant_id}')
async def update_variant(variant_id: str, body: dict, user: dict = Depends(require_auth)):
    db = get_db()
    upd = {k: v for k, v in body.items() if k not in ('id', '_id', 'created_at', 'created_by')}
    upd['updated_at'] = now_utc()
    await db.dewi_rnd_variants.update_one({'id': variant_id}, {'$set': upd})
    return {'ok': True}


@router.delete('/variants/{variant_id}')
async def delete_variant(variant_id: str, user: dict = Depends(require_auth)):
    db = get_db()
    await db.dewi_rnd_variants.delete_one({'id': variant_id})
    return {'ok': True}


# ──────────────────────────────────────────────────────────────────────────────
# PATTERNS & MARKING (Dokumentasi Pola)
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/patterns')
async def list_patterns(
    style_id: Optional[str] = None,
    search:   Optional[str] = None,
    user: dict = Depends(require_auth),
):
    db = get_db()
    q: dict = {}
    if style_id:
        q['style_id'] = style_id
    if search:
        q['$or'] = [
            {'pattern_code':  {'$regex': search, '$options': 'i'}},
            {'style_name':    {'$regex': search, '$options': 'i'}},
        ]
    docs = await db.dewi_rnd_patterns.find(q, {'_id': 0}).sort('created_at', -1).to_list(500)
    return [serialize(d) for d in docs]


@router.post('/patterns')
async def create_pattern(body: dict, user: dict = Depends(require_auth)):
    db = get_db()
    doc = {
        'id':            sid(),
        'pattern_code':  body.get('pattern_code', ''),
        'style_id':      body.get('style_id', ''),
        'style_code':    body.get('style_code', ''),
        'style_name':    body.get('style_name', ''),
        'size_range':    body.get('size_range', ''),      # e.g. "S-XL"
        'total_pieces':  body.get('total_pieces', 0),
        'fabric_width':  body.get('fabric_width', 150),   # cm
        'fabric_usage_per_pcs': body.get('fabric_usage_per_pcs', 0.0),  # meter
        'hpp_fabric_per_pcs':   body.get('hpp_fabric_per_pcs', 0.0),     # Rp
        'efficiency_pct':       body.get('efficiency_pct', 0.0),         # %
        'marking_photo_url':    body.get('marking_photo_url', None),
        'pattern_file_url':     body.get('pattern_file_url', None),
        'notes':         body.get('notes', ''),
        'status':        body.get('status', 'draft'),  # draft / approved
        'approved_by':   None,
        'approved_at':   None,
        'created_by':      user['id'],
        'created_by_name': user.get('name', ''),
        'created_at': now_utc(),
        'updated_at': now_utc(),
    }
    await db.dewi_rnd_patterns.insert_one(doc)
    return serialize(doc)


@router.put('/patterns/{pattern_id}')
async def update_pattern(pattern_id: str, body: dict, user: dict = Depends(require_auth)):
    db = get_db()
    upd = {k: v for k, v in body.items() if k not in ('id', '_id', 'created_at', 'created_by')}
    upd['updated_at'] = now_utc()
    await db.dewi_rnd_patterns.update_one({'id': pattern_id}, {'$set': upd})
    return {'ok': True}


@router.post('/patterns/{pattern_id}/approve')
async def approve_pattern(pattern_id: str, user: dict = Depends(require_auth)):
    db = get_db()
    await db.dewi_rnd_patterns.update_one(
        {'id': pattern_id},
        {'$set': {
            'status': 'approved',
            'approved_by': user.get('name', ''),
            'approved_at': now_utc(),
            'updated_at': now_utc(),
        }}
    )
    return {'ok': True}


@router.delete('/patterns/{pattern_id}')
async def delete_pattern(pattern_id: str, user: dict = Depends(require_auth)):
    db = get_db()
    await db.dewi_rnd_patterns.delete_one({'id': pattern_id})
    return {'ok': True}


# ── Marking Media Attachments (Session 27 — GAP-R4) ──────────────────────────
@router.post('/patterns/{pattern_id}/attach-media')
async def attach_pattern_media(pattern_id: str, body: dict, user: dict = Depends(require_auth)):
    """Attach uploaded media (foto/video marking) to a pattern.
    Body: { attachment_id, url, content_type, original_filename, size? }
    Returns the updated marking_media list.
    """
    db = get_db()
    pat = await db.dewi_rnd_patterns.find_one({'id': pattern_id})
    if not pat:
        raise HTTPException(404, 'Pattern not found')

    media_item = {
        'attachment_id': body.get('attachment_id') or '',
        'storage_path':  body.get('storage_path') or '',
        'url':           body.get('url') or '',
        'content_type':  body.get('content_type') or '',
        'original_filename': body.get('original_filename') or '',
        'size':          int(body.get('size') or 0),
        'kind':          'video' if (body.get('content_type') or '').startswith('video') else 'photo',
        'uploaded_by':   user.get('name', ''),
        'uploaded_by_id': user.get('id', ''),
        'uploaded_at':   now_utc(),
    }
    media_list = pat.get('marking_media') or []
    media_list.append(media_item)
    await db.dewi_rnd_patterns.update_one(
        {'id': pattern_id},
        {'$set': {'marking_media': media_list, 'updated_at': now_utc()}}
    )
    # ISO format datetime for return
    media_item_resp = {**media_item, 'uploaded_at': media_item['uploaded_at'].isoformat()}
    return {'ok': True, 'media': media_item_resp, 'total_media': len(media_list)}


@router.delete('/patterns/{pattern_id}/media/{attachment_id}')
async def remove_pattern_media(pattern_id: str, attachment_id: str, user: dict = Depends(require_auth)):
    """Remove a media reference from a pattern."""
    db = get_db()
    pat = await db.dewi_rnd_patterns.find_one({'id': pattern_id})
    if not pat:
        raise HTTPException(404, 'Pattern not found')

    media_list = [m for m in (pat.get('marking_media') or []) if m.get('attachment_id') != attachment_id]
    await db.dewi_rnd_patterns.update_one(
        {'id': pattern_id},
        {'$set': {'marking_media': media_list, 'updated_at': now_utc()}}
    )
    return {'ok': True, 'total_media': len(media_list)}


# ──────────────────────────────────────────────────────────────────────────────
# HPP CALCULATOR (Full Cost per Pcs → Harga Jual Proposal)
# ──────────────────────────────────────────────────────────────────────────────

def _calculate_hpp(body: dict) -> dict:
    """Core HPP calculation logic."""
    fabric_usage  = float(body.get('fabric_usage_per_pcs', 0) or 0)
    fabric_price  = float(body.get('fabric_price_per_meter', 0) or 0)
    accessories   = body.get('accessories_cost', [])   # list of {name, unit_cost, qty}
    cmt_cost      = float(body.get('cmt_cost_per_pcs', 0) or 0)
    cutting_cost  = float(body.get('cutting_cost_per_pcs', 0) or 0)
    packaging_cost= float(body.get('packaging_cost_per_pcs', 0) or 0)
    overhead_pct  = float(body.get('overhead_pct', 10) or 10)
    margin_pct    = float(body.get('margin_pct', 30) or 30)

    fabric_cost   = fabric_usage * fabric_price
    acc_total     = sum(float(a.get('unit_cost', 0) or 0) * float(a.get('qty', 1) or 1)
                        for a in accessories)
    direct_cost   = fabric_cost + acc_total + cmt_cost + cutting_cost + packaging_cost
    overhead_val  = direct_cost * overhead_pct / 100
    hpp_total     = direct_cost + overhead_val
    selling_price = hpp_total / (1 - margin_pct / 100) if margin_pct < 100 else hpp_total

    return {
        'fabric_cost':      round(fabric_cost, 2),
        'accessories_total':round(acc_total, 2),
        'cmt_cost':         round(cmt_cost, 2),
        'cutting_cost':     round(cutting_cost, 2),
        'packaging_cost':   round(packaging_cost, 2),
        'direct_cost':      round(direct_cost, 2),
        'overhead_value':   round(overhead_val, 2),
        'hpp_total':        round(hpp_total, 2),
        'selling_price_proposal': round(selling_price, 2),
        'margin_pct':       margin_pct,
        'overhead_pct':     overhead_pct,
    }


@router.get('/hpp-calculator')
async def list_hpp(
    style_id: Optional[str] = None,
    user: dict = Depends(require_auth),
):
    db = get_db()
    q = {}
    if style_id:
        q['style_id'] = style_id
    docs = await db.dewi_rnd_hpp.find(q, {'_id': 0}).sort('created_at', -1).to_list(200)
    return [serialize(d) for d in docs]


@router.post('/hpp-calculator')
async def create_hpp(body: dict, user: dict = Depends(require_auth)):
    db = get_db()
    calc = _calculate_hpp(body)
    doc = {
        'id':          sid(),
        'hpp_code':    body.get('hpp_code', f"HPP-{sid()[:6].upper()}"),
        'style_id':    body.get('style_id', ''),
        'style_code':  body.get('style_code', ''),
        'style_name':  body.get('style_name', ''),
        # Inputs
        'fabric_usage_per_pcs':    body.get('fabric_usage_per_pcs', 0),
        'fabric_price_per_meter':  body.get('fabric_price_per_meter', 0),
        'accessories_cost':        body.get('accessories_cost', []),
        'cmt_cost_per_pcs':        body.get('cmt_cost_per_pcs', 0),
        'cutting_cost_per_pcs':    body.get('cutting_cost_per_pcs', 0),
        'packaging_cost_per_pcs':  body.get('packaging_cost_per_pcs', 0),
        'overhead_pct':            body.get('overhead_pct', 10),
        'margin_pct':              body.get('margin_pct', 30),
        'notes':                   body.get('notes', ''),
        'status':                  body.get('status', 'draft'),
        # Calculated results
        **calc,
        'created_by':      user['id'],
        'created_by_name': user.get('name', ''),
        'created_at': now_utc(),
        'updated_at': now_utc(),
    }
    await db.dewi_rnd_hpp.insert_one(doc)
    return serialize(doc)


@router.put('/hpp-calculator/{calc_id}')
async def update_hpp(calc_id: str, body: dict, user: dict = Depends(require_auth)):
    db = get_db()
    calc = _calculate_hpp(body)
    upd = {k: v for k, v in body.items() if k not in ('id', '_id', 'created_at', 'created_by')}
    upd.update(calc)
    upd['updated_at'] = now_utc()
    await db.dewi_rnd_hpp.update_one({'id': calc_id}, {'$set': upd})
    doc = await db.dewi_rnd_hpp.find_one({'id': calc_id}, {'_id': 0})
    return serialize(doc)


@router.delete('/hpp-calculator/{calc_id}')
async def delete_hpp(calc_id: str, user: dict = Depends(require_auth)):
    db = get_db()
    await db.dewi_rnd_hpp.delete_one({'id': calc_id})
    return {'ok': True}


@router.post('/hpp-calculator/preview')
async def preview_hpp(body: dict, user: dict = Depends(require_auth)):
    """Calculate HPP on-the-fly without saving (for live preview)."""
    return _calculate_hpp(body)


# ──────────────────────────────────────────────────────────────────────────────
# TECH PACK (Dokumen teknis per style: BOM, konstruksi, grading)
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/tech-packs')
async def list_tech_packs(
    style_id: Optional[str] = None,
    search:   Optional[str] = None,
    user: dict = Depends(require_auth),
):
    db = get_db()
    q: dict = {}
    if style_id:
        q['style_id'] = style_id
    if search:
        q['$or'] = [
            {'style_code':  {'$regex': search, '$options': 'i'}},
            {'style_name':  {'$regex': search, '$options': 'i'}},
            {'version':     {'$regex': search, '$options': 'i'}},
        ]
    docs = await db.dewi_rnd_tech_packs.find(q, {'_id': 0}).sort('created_at', -1).to_list(200)
    return [serialize(d) for d in docs]


@router.post('/tech-packs')
async def create_tech_pack(body: dict, user: dict = Depends(require_auth)):
    db = get_db()
    doc = {
        'id':           sid(),
        'style_id':     body.get('style_id', ''),
        'style_code':   body.get('style_code', ''),
        'style_name':   body.get('style_name', ''),
        'version':      body.get('version', 'v1'),
        'doc_url':      body.get('doc_url', None),
        'doc_type':     body.get('doc_type', 'pdf'),   # pdf / image / link
        'title':        body.get('title', ''),
        'description':  body.get('description', ''),
        # Bill of Materials
        'bom_items':    body.get('bom_items', []),     # [{material, spec, qty, unit, supplier}]
        # Construction notes
        'construction_notes': body.get('construction_notes', ''),
        'stitch_type':        body.get('stitch_type', ''),
        'seam_allowance_mm':  body.get('seam_allowance_mm', 10),
        # Size grading
        'size_grading_notes': body.get('size_grading_notes', ''),
        'base_size':          body.get('base_size', 'M'),
        'size_range':         body.get('size_range', 'S-XL'),
        'measurements':       body.get('measurements', []),  # [{point, S, M, L, XL, XXL}]
        # Status
        'status':       body.get('status', 'draft'),   # draft / approved / superseded
        'approved_by':  None,
        'approved_at':  None,
        'is_latest':    True,
        'created_by':      user['id'],
        'created_by_name': user.get('name', ''),
        'created_at':   now_utc(),
        'updated_at':   now_utc(),
    }
    # Mark previous versions as non-latest
    if body.get('style_id'):
        await db.dewi_rnd_tech_packs.update_many(
            {'style_id': body['style_id'], 'is_latest': True},
            {'$set': {'is_latest': False}}
        )
    await db.dewi_rnd_tech_packs.insert_one(doc)
    return serialize(doc)


@router.get('/tech-packs/{tp_id}')
async def get_tech_pack(tp_id: str, user: dict = Depends(require_auth)):
    db = get_db()
    doc = await db.dewi_rnd_tech_packs.find_one({'id': tp_id}, {'_id': 0})
    if not doc:
        raise HTTPException(404, 'Tech pack tidak ditemukan')
    return serialize(doc)


@router.put('/tech-packs/{tp_id}')
async def update_tech_pack(tp_id: str, body: dict, user: dict = Depends(require_auth)):
    db = get_db()
    upd = {k: v for k, v in body.items() if k not in ('id', '_id', 'created_at', 'created_by')}
    upd['updated_at'] = now_utc()
    await db.dewi_rnd_tech_packs.update_one({'id': tp_id}, {'$set': upd})
    doc = await db.dewi_rnd_tech_packs.find_one({'id': tp_id}, {'_id': 0})
    return serialize(doc)


@router.post('/tech-packs/{tp_id}/approve')
async def approve_tech_pack(tp_id: str, user: dict = Depends(require_auth)):
    db = get_db()
    await db.dewi_rnd_tech_packs.update_one(
        {'id': tp_id},
        {'$set': {
            'status':      'approved',
            'approved_by':  user.get('name', ''),
            'approved_at':  now_utc(),
            'updated_at':   now_utc(),
        }}
    )
    return {'ok': True}


@router.delete('/tech-packs/{tp_id}')
async def delete_tech_pack(tp_id: str, user: dict = Depends(require_auth)):
    db = get_db()
    await db.dewi_rnd_tech_packs.delete_one({'id': tp_id})
    return {'ok': True}


# ──────────────────────────────────────────────────────────────────────────────
# STYLE OVERVIEW (semua data terkait per style — untuk detail page)
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/styles/{style_id}/overview')
async def get_style_overview(style_id: str, user: dict = Depends(require_auth)):
    """Return style + all linked documents: variants, samples, patterns, hpp, revisions, tech-packs"""
    db = get_db()

    style = await db.dewi_rnd_styles.find_one({'id': style_id}, {'_id': 0})
    if not style:
        raise HTTPException(404, 'Style tidak ditemukan')

    variants    = await db.dewi_rnd_variants.find({'style_id': style_id}, {'_id': 0}).to_list(100)
    samples     = await db.dewi_rnd_sample_requests.find({'style_id': style_id}, {'_id': 0}).sort('created_at', -1).to_list(50)
    patterns    = await db.dewi_rnd_patterns.find({'style_id': style_id}, {'_id': 0}).sort('created_at', -1).to_list(50)
    hpp_records = await db.dewi_rnd_hpp.find({'style_id': style_id}, {'_id': 0}).sort('created_at', -1).to_list(20)
    revisions   = await db.dewi_rnd_revisions.find({'style_id': style_id}, {'_id': 0}).sort('revision_number', -1).to_list(50)
    tech_packs  = await db.dewi_rnd_tech_packs.find({'style_id': style_id}, {'_id': 0}).sort('created_at', -1).to_list(20)
    costings    = await db.dewi_rnd_sample_costing.find({'style_id': style_id}, {'_id': 0}).sort('created_at', -1).to_list(20)

    def fmt_list(docs):
        out = []
        for d in docs:
            d2 = dict(d)
            for k, v in d2.items():
                if isinstance(v, datetime):
                    d2[k] = v.isoformat()
            out.append(d2)
        return out

    style2 = serialize(style)
    return {
        'style':      style2,
        'variants':   fmt_list(variants),
        'samples':    fmt_list(samples),
        'patterns':   fmt_list(patterns),
        'hpp_records':fmt_list(hpp_records),
        'revisions':  fmt_list(revisions),
        'tech_packs': fmt_list(tech_packs),
        'costings':   fmt_list(costings),
        'summary': {
            'total_variants':   len(variants),
            'total_samples':    len(samples),
            'total_patterns':   len(patterns),
            'total_hpp':        len(hpp_records),
            'total_revisions':  len(revisions),
            'total_tech_packs': len(tech_packs),
            'total_costings':   len(costings),
        }
    }


# ──────────────────────────────────────────────────────────────────────────────
# REVISIONS — tambahkan PUT (update)
# ──────────────────────────────────────────────────────────────────────────────

@router.put('/revisions/{revision_id}')
async def update_revision(revision_id: str, body: dict, user: dict = Depends(require_auth)):
    db = get_db()
    upd = {k: v for k, v in body.items() if k not in ('id', '_id', 'created_at', 'created_by')}
    upd['updated_at'] = now_utc()
    await db.dewi_rnd_revisions.update_one({'id': revision_id}, {'$set': upd})
    return {'ok': True}


# ──────────────────────────────────────────────────────────────────────────────
# ANALYTICS
# ──────────────────────────────────────────────────────────────────────────────

@router.get('/analytics')
async def get_analytics(user: dict = Depends(require_auth)):
    """Get RnD analytics"""
    db = get_db()
    
    total_styles = await db.dewi_rnd_styles.count_documents({})
    active_styles = await db.dewi_rnd_styles.count_documents({'status': 'active'})
    
    total_samples = await db.dewi_rnd_sample_requests.count_documents({})
    pending_samples = await db.dewi_rnd_sample_requests.count_documents({'status': 'submitted'})
    approved_samples = await db.dewi_rnd_sample_requests.count_documents({'status': 'approved'})
    
    total_materials = await db.dewi_rnd_materials.count_documents({})
    active_materials = await db.dewi_rnd_materials.count_documents({'status': 'active'})
    
    total_revisions = await db.dewi_rnd_revisions.count_documents({})
    
    return {
        'styles': {
            'total': total_styles,
            'active': active_styles,
        },
        'sample_requests': {
            'total': total_samples,
            'pending': pending_samples,
            'approved': approved_samples,
        },
        'materials': {
            'total': total_materials,
            'active': active_materials,
        },
        'revisions': {
            'total': total_revisions,
        },
    }

# ──────────────────────────────────────────────────────────────────────────────
# SEED DATA
# ──────────────────────────────────────────────────────────────────────────────

@router.post('/seed')
async def seed_rnd_data(
    reset: bool = Query(True, description='Hapus data demo lama sebelum seed'),
    user: dict = Depends(require_auth),
):
    """Seed demo RnD data — kaya & idempotent.

    Strategi:
      - Tag dokumen demo dengan flag `is_demo=True` agar tidak menabrak data riil.
      - Default `reset=true` → hapus hanya dokumen `is_demo=True` lalu insert ulang.
    """
    db = get_db()
    uid = user['id']
    uname = user.get('name', '')

    if reset:
        await db.dewi_rnd_styles.delete_many({'is_demo': True})
        await db.dewi_rnd_sample_requests.delete_many({'is_demo': True})
        await db.dewi_rnd_revisions.delete_many({'is_demo': True})
        await db.dewi_rnd_materials.delete_many({'is_demo': True})
        await db.dewi_rnd_sample_costing.delete_many({'is_demo': True})

    # ── STYLES ────────────────────────────────────────────────────────────
    style_seed = [
        ('ST-DEMO-001', 'Basic Tee Premium',     'T-Shirt', 'Zara',     'Cotton Combed 30s',  'Spring 2024', 'active', 'Classic crew neck t-shirt premium'),
        ('ST-DEMO-002', 'Polo Shirt Classic',    'Polo',    'Uniqlo',   'Pique Cotton',       'Summer 2024', 'active', 'Classic polo with collar'),
        ('ST-DEMO-003', 'Hoodie Oversized',      'Hoodie',  'H&M',      'Fleece Cotton 320',  'Fall 2024',   'active', 'Oversized hoodie streetwear'),
        ('ST-DEMO-004', 'Long Sleeve Heritage',  'T-Shirt', 'Zara',     'Cotton Combed 24s',  'Fall 2024',   'draft',  'Heritage style long sleeve'),
        ('ST-DEMO-005', 'Crewneck Sweatshirt',   'Sweater', 'Pull&Bear','Fleece Cotton 280',  'Winter 2024', 'active', 'Crewneck heavyweight sweatshirt'),
        ('ST-DEMO-006', 'Jogger Pants Slim',     'Pants',   'Uniqlo',   'Stretch Twill',      'Summer 2024', 'active', 'Slim fit jogger with elastic waist'),
        ('ST-DEMO-007', 'Bomber Jacket Light',   'Jacket',  'Pull&Bear','Nylon Taslan',       'Spring 2025', 'review', 'Lightweight bomber jacket'),
    ]
    styles = []
    for code, name, cat, buyer, fabric, season, status, desc in style_seed:
        styles.append({
            'id': sid(),
            'style_code': code,
            'style_name': name,
            'category': cat,
            'buyer': buyer,
            'fabric_type': fabric,
            'season': season,
            'description': desc,
            'status': status,
            'techpack_url': None,
            'techpack_name': None,
            'design_images': [],
            'variants': [
                {'size': 'S', 'color': 'Black', 'sku': f'{code}-S-BLK'},
                {'size': 'M', 'color': 'Black', 'sku': f'{code}-M-BLK'},
                {'size': 'L', 'color': 'White', 'sku': f'{code}-L-WHT'},
            ],
            'is_demo': True,
            'created_by': uid,
            'created_by_name': uname,
            'created_at': now_utc(),
            'updated_at': now_utc(),
        })
    if styles:
        await db.dewi_rnd_styles.insert_many(styles)

    # ── MATERIALS ─────────────────────────────────────────────────────────
    material_seed = [
        ('FAB-DEMO-001', 'Cotton Combed 30s',  'Fabric',    'PT Textile Indo',   '100% Cotton',                 180, 25000,  100, 'Shrinkage: 3%, Color fastness: Grade 4',   'Premium segment'),
        ('FAB-DEMO-002', 'Pique Cotton',       'Fabric',    'PT Textile Indo',   '100% Cotton',                 220, 35000,  100, 'Shrinkage: 2%, Color fastness: Grade 4-5', 'Polo shirt'),
        ('FAB-DEMO-003', 'Fleece Cotton 320',  'Fabric',    'PT Sentral Kain',   '80% Cotton, 20% Polyester',   320, 55000,  150, 'Shrinkage: 4%, Pilling: Grade 4',          'Heavy hoodie'),
        ('FAB-DEMO-004', 'Stretch Twill',      'Fabric',    'PT Sentral Kain',   '97% Cotton, 3% Spandex',      230, 42000,  150, 'Stretch recovery: 90%',                    'Jogger pants'),
        ('FAB-DEMO-005', 'Nylon Taslan',       'Fabric',    'PT Bahan Asia',     '100% Nylon',                   90, 38000,  200, 'Water repellent: Grade 4',                 'Light jacket'),
        ('AKS-DEMO-001', 'Tag Karton Premium', 'Accessory', 'PT Aksesoris Jaya', 'Karton 300gsm + Foil',         12,  1200, 1000, 'Print quality: A',                         'Branding tag'),
        ('AKS-DEMO-002', 'Resleting YKK 7"',   'Accessory', 'YKK Indonesia',     'Metal Brass',                  10,  4500,  500, 'Cycle test: 5000+',                        'Jacket / Pants'),
        ('BNG-DEMO-001', 'Benang Polyester',   'Thread',    'PT Benang Sentosa', '100% Polyester Spun',           1,  3500,  100, 'Tensile: high',                            'General sewing'),
    ]
    materials = []
    for code, name, cat, vendor, comp, weight, price, moq, test, notes in material_seed:
        materials.append({
            'id': sid(),
            'material_code': code,
            'material_name': name,
            'category': cat,
            'vendor': vendor,
            'composition': comp,
            'weight': weight,
            'price_per_meter': price,
            'min_order_qty': moq,
            'test_results': test,
            'notes': notes,
            'status': 'active',
            'is_demo': True,
            'created_by': uid,
            'created_by_name': uname,
            'created_at': now_utc(),
            'updated_at': now_utc(),
        })
    if materials:
        await db.dewi_rnd_materials.insert_many(materials)

    # ── SAMPLE REQUESTS ──────────────────────────────────────────────────
    today_str = datetime.now().strftime('%Y%m%d')
    sample_specs = [
        (styles[0], 5,  'high',   2,  'submitted', None,       'Urgent for client presentation'),
        (styles[1], 3,  'normal', 5,  'approved',  'approved', 'Standard sample run'),
        (styles[2], 6,  'high',   3,  'submitted', None,       'Pre-production for Fall capsule'),
        (styles[3], 4,  'low',    10, 'draft',     None,       'Initial sketch — pending design lock'),
        (styles[4], 3,  'normal', 7,  'approved',  'approved', 'Confirmed by buyer'),
        (styles[5], 8,  'high',   4,  'rejected',  'rejected', 'Fabric stretch insufficient'),
    ]
    sample_requests = []
    for idx, (style, qty, prio, due_days, status, approval, notes) in enumerate(sample_specs, start=1):
        is_decided = status in ('approved', 'rejected')
        sample_requests.append({
            'id': sid(),
            'sample_code': f'SR-DEMO-{today_str}-{idx:03d}',
            'style_id': style['id'],
            'style_code': style['style_code'],
            'style_name': style['style_name'],
            'quantity': qty,
            'priority': prio,
            'due_date': (now_utc() + timedelta(days=due_days)).isoformat(),
            'notes': notes,
            'status': status,
            'approval_status': approval,
            'approved_by': uid if is_decided else None,
            'approved_by_name': uname if is_decided else None,
            'approved_at': now_utc() if is_decided else None,
            'approval_notes': ('Looks good' if approval == 'approved'
                                else 'Need revision' if approval == 'rejected'
                                else None),
            'is_demo': True,
            'created_by': uid,
            'created_by_name': uname,
            'created_at': now_utc(),
            'updated_at': now_utc(),
        })
    if sample_requests:
        await db.dewi_rnd_sample_requests.insert_many(sample_requests)

    # ── REVISIONS ────────────────────────────────────────────────────────
    revisions = []
    rev_specs = [
        (styles[0], 'Rev 1 — Logo Update',     'Reposition logo dada kiri',          'Permintaan buyer'),
        (styles[0], 'Rev 2 — Fit Adjustment',  'Body length +2cm, sleeve +1cm',      'Hasil fitting sample 1'),
        (styles[2], 'Rev 1 — Pocket Detail',   'Tambah hidden pocket di dalam',      'Request brand identity'),
        (styles[3], 'Rev 1 — Color Block',     'Sleeve kontras warna abu',           'Trend research Fall 24'),
        (styles[6], 'Rev 1 — Lining Change',   'Ganti lining ke mesh untuk breath',  'Feedback wear-test'),
    ]
    rev_counter = {}
    for style, name, summary, reason in rev_specs:
        n = rev_counter.get(style['id'], 0) + 1
        rev_counter[style['id']] = n
        revisions.append({
            'id': sid(),
            'style_id': style['id'],
            'style_code': style['style_code'],
            'revision_number': n,
            'revision_name': name,
            'changes_summary': summary,
            'reason': reason,
            'previous_revision_id': None,
            'is_demo': True,
            'created_by': uid,
            'created_by_name': uname,
            'created_at': now_utc(),
        })
    if revisions:
        await db.dewi_rnd_revisions.insert_many(revisions)

    # ── SAMPLE COSTING (untuk SR yang sudah approved) ────────────────────
    costing = []
    for sr in sample_requests:
        if sr['status'] != 'approved':
            continue
        bom_lines = [
            {'material_code': materials[0]['material_code'], 'material_name': materials[0]['material_name'], 'qty': 1.5,  'unit': 'm',   'unit_cost': materials[0]['price_per_meter'], 'total_cost': int(1.5 * materials[0]['price_per_meter'])},
            {'material_code': materials[5]['material_code'], 'material_name': materials[5]['material_name'], 'qty': 1,    'unit': 'pcs', 'unit_cost': materials[5]['price_per_meter'], 'total_cost': materials[5]['price_per_meter']},
            {'material_code': materials[7]['material_code'], 'material_name': materials[7]['material_name'], 'qty': 200,  'unit': 'm',   'unit_cost': materials[7]['price_per_meter'], 'total_cost': 200 * materials[7]['price_per_meter']},
        ]
        total_material = sum(line['total_cost'] for line in bom_lines)
        labor = 25000
        overhead = 10000
        costing.append({
            'id': sid(),
            'sample_request_id': sr['id'],
            'sample_code': sr['sample_code'],
            'bom_lines': bom_lines,
            'total_material_cost': total_material,
            'labor_cost': labor,
            'overhead_cost': overhead,
            'total_cost': total_material + labor + overhead,
            'notes': 'Costing demo — perkiraan untuk presentasi internal',
            'is_demo': True,
            'created_by': uid,
            'created_by_name': uname,
            'created_at': now_utc(),
            'updated_at': now_utc(),
        })
    if costing:
        await db.dewi_rnd_sample_costing.insert_many(costing)

    return {
        'success': True,
        'reset': reset,
        'styles': len(styles),
        'materials': len(materials),
        'sample_requests': len(sample_requests),
        'revisions': len(revisions),
        'sample_costing': len(costing),
    }
