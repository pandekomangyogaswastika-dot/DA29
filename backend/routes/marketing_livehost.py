"""
CV. Dewi Aditya — Marketing Portal: LiveHost Management

LiveHost = Host yang di-hire perusahaan untuk live streaming (bukan influencer).
Berbeda dengan KOL/Creator yang punya followers sendiri.

Key Features:
- Shift scheduling & management (morning, afternoon, evening, night)
- Clock in/out tracking (simple timestamp)
- Performance tracking per shift (viewers, revenue, orders)
- Script library & training modules
- Payment calculation (hourly rate + bonus - penalty)
- Auto-sync payment to Finance/Payroll
- Real-time WebSocket notifications

Collections:
- marketing_livehosts: LiveHost profiles
- marketing_livehost_shifts: Shift schedule & performance
- marketing_livehost_scripts: Script library
- marketing_livehost_training: Training modules
- marketing_livehost_training_progress: Training completion tracking

Author: CV. Dewi Aditya Development Team
Date: 2026-05-21
"""

import uuid
import os
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request, Query, UploadFile, File, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from database import get_db
from auth import JWT_SECRET, hash_password, verify_password, require_auth, serialize_doc, log_activity
import jwt as pyjwt

router = APIRouter(prefix='/api/marketing/livehost', tags=['Marketing-LiveHost'])

# UUID v4 path pattern — used to constrain /{host_id} so it doesn't capture
# static segments like /shifts, /scripts, /training, /payment, /analytics, /portal
UUID_PATH_REGEX = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'

LIVEHOST_TOKEN_AUDIENCE = 'livehost-portal'
LIVEHOST_TOKEN_HOURS = 24
UPLOAD_DIR = '/app/uploads/livehost'

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(f'{UPLOAD_DIR}/scripts', exist_ok=True)
os.makedirs(f'{UPLOAD_DIR}/training', exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _uid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


def _get_user(request: Request) -> dict:
    return getattr(request.state, 'user', {"id": "system", "email": "system", "role": "admin"})


def _create_livehost_token(host: dict) -> str:
    """Create JWT token for LiveHost portal"""
    payload = {
        'sub': host['id'],
        'email': host['email'],
        'host_id': host['id'],
        'host_name': host.get('name', ''),
        'aud': LIVEHOST_TOKEN_AUDIENCE,
        'exp': _now() + timedelta(hours=LIVEHOST_TOKEN_HOURS),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm='HS256')


def _decode_livehost_token(token: str) -> Optional[dict]:
    """Decode and validate LiveHost JWT token"""
    try:
        return pyjwt.decode(
            token, JWT_SECRET, algorithms=['HS256'], audience=LIVEHOST_TOKEN_AUDIENCE
        )
    except Exception:
        return None


async def require_livehost_auth(request: Request) -> dict:
    """Require LiveHost portal authentication"""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        raise HTTPException(401, 'Token tidak ditemukan')
    token = auth.split(' ', 1)[1]
    payload = _decode_livehost_token(token)
    if not payload:
        raise HTTPException(401, 'Token tidak valid atau kadaluarsa')
    db = get_db()
    host = await db.marketing_livehosts.find_one({'id': payload.get('host_id')}, {'_id': 0})
    if not host or host.get('status') != 'active':
        raise HTTPException(403, 'Akun LiveHost tidak aktif')
    host.pop('password_hash', None)
    return host


# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════════════════

class LiveHostCreate(BaseModel):
    name: str = Field(..., min_length=1, description="LiveHost name")
    email: str = Field(..., description="Email for portal login")
    password: str = Field(..., min_length=6, description="Portal password")
    phone: Optional[str] = None
    employment_type: str = Field("part_time", description="full_time | part_time | freelance | contract")
    hourly_rate: float = Field(0, ge=0, description="Hourly rate in Rupiah")
    shift_preferences: Optional[List[str]] = Field(default_factory=list, description="morning | afternoon | evening | night")
    language_skills: Optional[List[str]] = Field(default_factory=list, description="indonesia | english | mandarin")
    product_expertise: Optional[List[str]] = Field(default_factory=list, description="fashion | electronics | food | beauty")
    assigned_account_ids: Optional[List[str]] = Field(default_factory=list, description="Platform account IDs")
    notes: Optional[str] = None


class LiveHostUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)
    phone: Optional[str] = None
    employment_type: Optional[str] = None
    hourly_rate: Optional[float] = Field(None, ge=0)
    shift_preferences: Optional[List[str]] = None
    language_skills: Optional[List[str]] = None
    product_expertise: Optional[List[str]] = None
    assigned_account_ids: Optional[List[str]] = None
    status: Optional[str] = Field(None, description="active | inactive | on_leave")
    notes: Optional[str] = None


class ShiftCreate(BaseModel):
    host_id: str
    account_id: str
    date: str = Field(..., description="YYYY-MM-DD")
    shift_type: str = Field(..., description="morning | afternoon | evening | night | custom")
    shift_start_time: str = Field(..., description="HH:MM (24-hour format)")
    shift_end_time: str = Field(..., description="HH:MM (24-hour format)")
    notes: Optional[str] = None


class ShiftUpdate(BaseModel):
    host_id: Optional[str] = None
    account_id: Optional[str] = None
    date: Optional[str] = None
    shift_type: Optional[str] = None
    shift_start_time: Optional[str] = None
    shift_end_time: Optional[str] = None
    notes: Optional[str] = None


class ClockInOut(BaseModel):
    shift_id: str
    action: str = Field(..., description="clock_in | clock_out")


class ShiftPerformanceRecord(BaseModel):
    shift_id: str
    platform: str = Field(..., description="shopee | tiktokshop | tokopedia")
    viewers: int = Field(0, ge=0)
    peak_viewers: int = Field(0, ge=0)
    revenue: float = Field(0, ge=0)
    orders: int = Field(0, ge=0)
    items_promoted: Optional[List[str]] = Field(default_factory=list)
    script_ids_used: Optional[List[str]] = Field(default_factory=list)
    script_adherence_score: Optional[int] = Field(None, ge=0, le=100)
    challenges_faced: Optional[str] = None
    notes: Optional[str] = None


class ScriptCreate(BaseModel):
    title: str = Field(..., min_length=1)
    category: str = Field(..., description="opening | demo | promo | closing | faq | objection_handling")
    account_id: Optional[str] = Field(None, description="Specific account or null for global")
    script_text: str = Field(..., min_length=1)
    language: str = Field("indonesia", description="indonesia | english | mandarin")
    products_applicable: Optional[List[str]] = Field(default_factory=list)


class TrainingCreate(BaseModel):
    title: str = Field(..., min_length=1)
    category: str = Field(..., description="product_knowledge | platform_rules | engagement | sales_techniques")
    description: str
    content_type: str = Field(..., description="video | pdf | quiz | external_link")
    content_url: Optional[str] = None  # Will be set after file upload
    duration_minutes: int = Field(0, ge=0)
    is_required: bool = True
    expiry_months: Optional[int] = Field(None, ge=1, description="Re-certification required every N months")
    passing_score: Optional[int] = Field(None, ge=0, le=100, description="For quiz type")


class TrainingAssign(BaseModel):
    host_ids: List[str]
    training_id: str


class TrainingComplete(BaseModel):
    training_id: str
    score: Optional[int] = Field(None, ge=0, le=100)


class LiveHostLoginIn(BaseModel):
    email: str
    password: str


# ══════════════════════════════════════════════════════════════════════════════
# LIVEHOST CRUD (ADMIN)
# ══════════════════════════════════════════════════════════════════════════════

@router.post('')
async def create_livehost(data: LiveHostCreate, request: Request):
    """Admin creates a new LiveHost"""
    await require_auth(request)
    db = get_db()
    
    # Check duplicate email
    if await db.marketing_livehosts.find_one({'email': data.email.lower().strip()}):
        raise HTTPException(400, f"Email '{data.email}' sudah terdaftar")
    
    host = {
        'id': _uid(),
        'name': data.name,
        'email': data.email.lower().strip(),
        'password_hash': hash_password(data.password),
        'phone': data.phone or '',
        'employment_type': data.employment_type,
        'hourly_rate': data.hourly_rate,
        'shift_preferences': data.shift_preferences or [],
        'language_skills': data.language_skills or [],
        'product_expertise': data.product_expertise or [],
        'assigned_account_ids': data.assigned_account_ids or [],
        'status': 'active',
        'notes': data.notes or '',
        'training_completed': [],
        'certification_expiry': {},
        'created_at': _now(),
        'created_by': _get_user(request).get('email', 'system'),
        'last_login_at': None,
    }
    
    await db.marketing_livehosts.insert_one(host)
    
    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'create', 'marketing_livehost',
        f"Created LiveHost: {data.name} ({data.email})"
    )
    
    host_safe = {**host}
    host_safe.pop('password_hash', None)
    return serialize_doc({'message': 'LiveHost berhasil dibuat', 'host': host_safe})


@router.get('')
async def list_livehosts(
    request: Request,
    status: Optional[str] = Query(None),
    employment_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """Admin lists all LiveHosts with filters"""
    await require_auth(request)
    db = get_db()
    
    query = {}
    if status:
        query['status'] = status
    if employment_type:
        query['employment_type'] = employment_type
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}},
        ]
    
    hosts = await db.marketing_livehosts.find(
        query, {'_id': 0, 'password_hash': 0}
    ).sort('name', 1).to_list(500)
    
    # Enrich dengan assigned account names
    if hosts:
        account_ids = list(set(aid for h in hosts for aid in h.get('assigned_account_ids', [])))
        if account_ids:
            accounts = await db.marketing_platform_accounts.find(
                {'id': {'$in': account_ids}}, {'_id': 0, 'id': 1, 'account_name': 1}
            ).to_list(500)
            account_map = {a['id']: a['account_name'] for a in accounts}
            for host in hosts:
                host['assigned_accounts'] = [
                    {'id': aid, 'name': account_map.get(aid, 'Unknown')}
                    for aid in host.get('assigned_account_ids', [])
                ]
    
    return serialize_doc(hosts)


# NOTE: Routes for `/{host_id}` (GET/PATCH/DELETE) are intentionally defined at the
# BOTTOM of this file. This is required because FastAPI evaluates routes in
# declaration order: putting `/{host_id}` here would cause static single-segment
# routes like `/shifts`, `/scripts`, `/training` to be incorrectly matched as
# `host_id="shifts"` etc. They are placed at the end so all static routes are
# registered first. See the "DYNAMIC HOST ID ROUTES" section near the end.


# ══════════════════════════════════════════════════════════════════════════════
# SHIFT MANAGEMENT (ADMIN)
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/shifts')
async def create_shift(data: ShiftCreate, request: Request):
    """Admin creates a shift assignment"""
    await require_auth(request)
    db = get_db()
    
    # Validate host
    host = await db.marketing_livehosts.find_one({'id': data.host_id}, {'_id': 0})
    if not host:
        raise HTTPException(404, 'LiveHost tidak ditemukan')
    if host.get('status') != 'active':
        raise HTTPException(400, 'LiveHost tidak aktif')
    
    # Validate account
    account = await db.marketing_platform_accounts.find_one({'id': data.account_id}, {'_id': 0})
    if not account:
        raise HTTPException(404, 'Platform account tidak ditemukan')
    
    # Check shift conflict (same host, same date, overlapping time)
    existing_shifts = await db.marketing_livehost_shifts.find({
        'host_id': data.host_id,
        'date': data.date,
    }, {'_id': 0}).to_list(100)
    
    for existing in existing_shifts:
        # Simple time overlap check
        if (data.shift_start_time < existing['shift_end_time'] and 
            data.shift_end_time > existing['shift_start_time']):
            raise HTTPException(
                400, 
                f"Conflict: Host sudah ada shift pada {data.date} ({existing['shift_start_time']}-{existing['shift_end_time']})"
            )
    
    # Calculate scheduled duration
    try:
        start_h, start_m = map(int, data.shift_start_time.split(':'))
        end_h, end_m = map(int, data.shift_end_time.split(':'))
        scheduled_duration_minutes = (end_h * 60 + end_m) - (start_h * 60 + start_m)
        if scheduled_duration_minutes <= 0:
            scheduled_duration_minutes += 24 * 60  # Next day
    except:
        raise HTTPException(400, 'Format waktu tidak valid (gunakan HH:MM)')
    
    shift = {
        'id': _uid(),
        'host_id': data.host_id,
        'host_name': host['name'],
        'account_id': data.account_id,
        'account_name': account['account_name'],
        'date': data.date,
        'shift_type': data.shift_type,
        'shift_start_time': data.shift_start_time,
        'shift_end_time': data.shift_end_time,
        'scheduled_duration_minutes': scheduled_duration_minutes,
        
        # Attendance (will be filled during clock in/out)
        'clock_in_time': None,
        'clock_out_time': None,
        'actual_duration_minutes': None,
        'attendance_status': 'scheduled',  # scheduled | on_time | late | no_show | completed
        
        # Performance (will be filled after shift)
        'platform': None,
        'viewers': 0,
        'peak_viewers': 0,
        'revenue': 0,
        'orders': 0,
        'items_promoted': [],
        
        # Script & Training
        'script_ids_used': [],
        'script_adherence_score': None,
        
        # Notes
        'notes': data.notes or '',
        'challenges_faced': '',
        'screenshot_url': None,
        
        # Payment (will be calculated after completion)
        'base_pay': 0,
        'bonus': 0,
        'penalty': 0,
        'total_pay': 0,
        'payment_status': 'pending',  # pending | calculated | synced_to_finance
        
        'created_at': _now(),
        'created_by': _get_user(request).get('email', 'system'),
        'reviewed_by': None,
        'reviewed_at': None,
    }
    
    await db.marketing_livehost_shifts.insert_one(shift)
    
    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'create', 'marketing_livehost_shift',
        f"Created shift for {host['name']} on {data.date} ({data.shift_start_time}-{data.shift_end_time})"
    )

    # SSE: notify host about new shift assignment
    try:
        await publish_livehost_notification(
            db,
            host_id=data.host_id,
            type_='shift_assigned',
            severity='info',
            title='Shift Baru Assigned',
            message=f"Shift {data.shift_type} pada {data.date} ({data.shift_start_time}-{data.shift_end_time}) di {account['account_name']}",
            link=f"/shifts/{shift['id']}",
        )
    except Exception:
        pass

    return serialize_doc({'message': 'Shift berhasil dibuat', 'shift': shift})


@router.get('/shifts')
async def list_shifts(
    request: Request,
    host_id: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    attendance_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    """Admin lists shifts with filters and pagination"""
    await require_auth(request)
    db = get_db()
    
    query = {}
    if host_id:
        query['host_id'] = host_id
    if account_id:
        query['account_id'] = account_id
    if date_from or date_to:
        query['date'] = {}
        if date_from:
            query['date']['$gte'] = date_from
        if date_to:
            query['date']['$lte'] = date_to
    if attendance_status:
        query['attendance_status'] = attendance_status
    
    total = await db.marketing_livehost_shifts.count_documents(query)
    skip = (page - 1) * limit
    
    shifts = await db.marketing_livehost_shifts.find(
        query, {'_id': 0}
    ).sort('date', -1).skip(skip).limit(limit).to_list(500)
    
    return serialize_doc({
        'shifts': shifts,
        'pagination': {
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit if total > 0 else 1,
            'has_next': skip + limit < total,
            'has_prev': page > 1,
        }
    })


@router.get('/shifts/calendar')
async def get_shifts_calendar(
    request: Request,
    date_from: str = Query(..., description="YYYY-MM-DD"),
    date_to: str = Query(..., description="YYYY-MM-DD"),
    host_id: Optional[str] = Query(None),
):
    """Get shifts for calendar view (weekly/monthly)"""
    await require_auth(request)
    db = get_db()
    
    query = {
        'date': {'$gte': date_from, '$lte': date_to}
    }
    if host_id:
        query['host_id'] = host_id
    
    shifts = await db.marketing_livehost_shifts.find(
        query, {'_id': 0}
    ).sort('date', 1).to_list(500)
    
    # Group by date for easy rendering
    calendar = {}
    for shift in shifts:
        date = shift['date']
        if date not in calendar:
            calendar[date] = []
        calendar[date].append(shift)
    
    return serialize_doc({
        'date_from': date_from,
        'date_to': date_to,
        'calendar': calendar,
        'total_shifts': len(shifts),
    })


@router.patch('/shifts/{shift_id}')
async def update_shift(shift_id: str, data: ShiftUpdate, request: Request):
    """Admin updates shift details"""
    await require_auth(request)
    db = get_db()
    
    shift = await db.marketing_livehost_shifts.find_one({'id': shift_id}, {'_id': 0})
    if not shift:
        raise HTTPException(404, 'Shift tidak ditemukan')
    
    update_data = {}
    if data.host_id is not None:
        host = await db.marketing_livehosts.find_one({'id': data.host_id}, {'_id': 0})
        if not host:
            raise HTTPException(404, 'LiveHost tidak ditemukan')
        update_data['host_id'] = data.host_id
        update_data['host_name'] = host['name']
    if data.account_id is not None:
        account = await db.marketing_platform_accounts.find_one({'id': data.account_id}, {'_id': 0})
        if not account:
            raise HTTPException(404, 'Platform account tidak ditemukan')
        update_data['account_id'] = data.account_id
        update_data['account_name'] = account['account_name']
    if data.date is not None:
        update_data['date'] = data.date
    if data.shift_type is not None:
        update_data['shift_type'] = data.shift_type
    if data.shift_start_time is not None:
        update_data['shift_start_time'] = data.shift_start_time
    if data.shift_end_time is not None:
        update_data['shift_end_time'] = data.shift_end_time
    if data.notes is not None:
        update_data['notes'] = data.notes
    
    # Recalculate duration if time changed
    if data.shift_start_time or data.shift_end_time:
        start_time = data.shift_start_time or shift['shift_start_time']
        end_time = data.shift_end_time or shift['shift_end_time']
        try:
            start_h, start_m = map(int, start_time.split(':'))
            end_h, end_m = map(int, end_time.split(':'))
            scheduled_duration_minutes = (end_h * 60 + end_m) - (start_h * 60 + start_m)
            if scheduled_duration_minutes <= 0:
                scheduled_duration_minutes += 24 * 60
            update_data['scheduled_duration_minutes'] = scheduled_duration_minutes
        except:
            pass
    
    update_data['updated_at'] = _now()
    
    await db.marketing_livehost_shifts.update_one({'id': shift_id}, {'$set': update_data})
    
    return serialize_doc({'message': 'Shift berhasil diupdate'})


@router.delete('/shifts/{shift_id}')
async def delete_shift(shift_id: str, request: Request):
    """Admin deletes shift"""
    await require_auth(request)
    db = get_db()
    
    shift = await db.marketing_livehost_shifts.find_one({'id': shift_id}, {'_id': 0})
    if not shift:
        raise HTTPException(404, 'Shift tidak ditemukan')
    
    # Only allow delete if not yet clocked in
    if shift.get('clock_in_time'):
        raise HTTPException(400, 'Tidak dapat menghapus shift yang sudah dimulai. Gunakan update status.')
    
    await db.marketing_livehost_shifts.delete_one({'id': shift_id})
    
    return serialize_doc({'message': 'Shift berhasil dihapus'})


# ══════════════════════════════════════════════════════════════════════════════
# CLOCK IN/OUT
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/clock')
async def clock_in_out(data: ClockInOut, request: Request):
    """LiveHost or Admin clock in/out for a shift (simple timestamp)"""
    # Can be called by admin OR livehost portal
    try:
        await require_auth(request)
        caller = 'admin'
    except:
        host = await require_livehost_auth(request)
        caller = 'livehost'
    
    db = get_db()
    shift = await db.marketing_livehost_shifts.find_one({'id': data.shift_id}, {'_id': 0})
    if not shift:
        raise HTTPException(404, 'Shift tidak ditemukan')
    
    now = _now()
    
    if data.action == 'clock_in':
        if shift.get('clock_in_time'):
            raise HTTPException(400, 'Shift sudah di-clock in')
        
        # Determine attendance status (on_time or late)
        # Simple check: if clock_in > 15 minutes after shift_start_time, mark as late
        shift_date_str = shift['date']
        shift_start_str = shift['shift_start_time']
        scheduled_datetime_str = f"{shift_date_str}T{shift_start_str}:00+00:00"
        try:
            scheduled_datetime = datetime.fromisoformat(scheduled_datetime_str.replace('+00:00', '')).replace(tzinfo=timezone.utc)
            time_diff = (now - scheduled_datetime).total_seconds() / 60
            if time_diff > 15:
                attendance_status = 'late'
            else:
                attendance_status = 'on_time'
        except:
            attendance_status = 'on_time'
        
        update_data = {
            'clock_in_time': now,
            'attendance_status': attendance_status,
        }
        
        await db.marketing_livehost_shifts.update_one({'id': data.shift_id}, {'$set': update_data})
        
        return serialize_doc({
            'message': f"Clock in berhasil ({attendance_status})",
            'clock_in_time': now,
            'attendance_status': attendance_status,
        })
    
    elif data.action == 'clock_out':
        if not shift.get('clock_in_time'):
            raise HTTPException(400, 'Shift belum di-clock in')
        if shift.get('clock_out_time'):
            raise HTTPException(400, 'Shift sudah di-clock out')
        
        clock_in_time = shift['clock_in_time']
        # Ensure clock_in_time is timezone-aware
        if clock_in_time.tzinfo is None:
            clock_in_time = clock_in_time.replace(tzinfo=timezone.utc)
        
        actual_duration_minutes = int((now - clock_in_time).total_seconds() / 60)
        
        update_data = {
            'clock_out_time': now,
            'actual_duration_minutes': actual_duration_minutes,
            'attendance_status': 'completed',
        }
        
        await db.marketing_livehost_shifts.update_one({'id': data.shift_id}, {'$set': update_data})
        
        return serialize_doc({
            'message': 'Clock out berhasil',
            'clock_out_time': now,
            'actual_duration_minutes': actual_duration_minutes,
        })
    
    else:
        raise HTTPException(400, 'Action harus clock_in atau clock_out')


# ══════════════════════════════════════════════════════════════════════════════
# SHIFT PERFORMANCE RECORDING
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/shifts/{shift_id}/performance')
async def record_shift_performance(shift_id: str, data: ShiftPerformanceRecord, request: Request):
    """Admin or LiveHost records performance for a completed shift"""
    # Can be called by admin OR livehost portal
    try:
        await require_auth(request)
        caller_email = _get_user(request).get('email', 'admin')
    except:
        host = await require_livehost_auth(request)
        caller_email = host['email']
    
    db = get_db()
    
    if data.shift_id != shift_id:
        raise HTTPException(400, 'Shift ID tidak cocok')
    
    shift = await db.marketing_livehost_shifts.find_one({'id': shift_id}, {'_id': 0})
    if not shift:
        raise HTTPException(404, 'Shift tidak ditemukan')
    
    if not shift.get('clock_out_time'):
        raise HTTPException(400, 'Shift belum di-clock out. Selesaikan shift terlebih dahulu.')
    
    update_data = {
        'platform': data.platform,
        'viewers': data.viewers,
        'peak_viewers': data.peak_viewers,
        'revenue': data.revenue,
        'orders': data.orders,
        'items_promoted': data.items_promoted or [],
        'script_ids_used': data.script_ids_used or [],
        'script_adherence_score': data.script_adherence_score,
        'challenges_faced': data.challenges_faced or '',
        'notes': shift.get('notes', '') + '\n' + (data.notes or ''),
        'reviewed_by': caller_email,
        'reviewed_at': _now(),
    }
    
    await db.marketing_livehost_shifts.update_one({'id': shift_id}, {'$set': update_data})
    
    return serialize_doc({'message': 'Performance shift berhasil dicatat'})


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2: SCRIPT LIBRARY & TRAINING MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/scripts')
async def create_script(data: ScriptCreate, request: Request):
    """Admin creates a script"""
    await require_auth(request)
    db = get_db()
    
    script = {
        'id': _uid(),
        'title': data.title,
        'category': data.category,
        'account_id': data.account_id,
        'script_text': data.script_text,
        'language': data.language,
        'products_applicable': data.products_applicable or [],
        'is_active': True,
        'created_at': _now(),
        'created_by': _get_user(request).get('email', 'system'),
    }
    
    await db.marketing_livehost_scripts.insert_one(script)
    
    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'create', 'marketing_livehost_script',
        f"Created script: {data.title}"
    )
    
    return serialize_doc({'message': 'Script berhasil dibuat', 'script': script})


@router.get('/scripts')
async def list_scripts(
    request: Request,
    category: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """Admin lists all scripts"""
    await require_auth(request)
    db = get_db()
    
    query = {'is_active': True}
    if category:
        query['category'] = category
    if account_id:
        query['account_id'] = account_id
    if language:
        query['language'] = language
    if search:
        query['$or'] = [
            {'title': {'$regex': search, '$options': 'i'}},
            {'script_text': {'$regex': search, '$options': 'i'}},
        ]
    
    scripts = await db.marketing_livehost_scripts.find(
        query, {'_id': 0}
    ).sort('created_at', -1).to_list(500)
    
    # Enrich dengan account name
    if scripts:
        account_ids = list(set(s['account_id'] for s in scripts if s.get('account_id')))
        if account_ids:
            accounts = await db.marketing_platform_accounts.find(
                {'id': {'$in': account_ids}}, {'_id': 0, 'id': 1, 'account_name': 1}
            ).to_list(500)
            account_map = {a['id']: a['account_name'] for a in accounts}
            for script in scripts:
                if script.get('account_id'):
                    script['account_name'] = account_map.get(script['account_id'], 'Unknown')
                else:
                    script['account_name'] = 'Global (All Accounts)'
    
    return serialize_doc(scripts)


@router.get('/scripts/{script_id}')
async def get_script(script_id: str, request: Request):
    """Admin gets script detail"""
    await require_auth(request)
    db = get_db()
    
    script = await db.marketing_livehost_scripts.find_one({'id': script_id}, {'_id': 0})
    if not script:
        raise HTTPException(404, 'Script tidak ditemukan')
    
    return serialize_doc(script)


@router.put('/scripts/{script_id}')
async def update_script(script_id: str, data: ScriptCreate, request: Request):
    """Admin updates script"""
    await require_auth(request)
    db = get_db()
    
    script = await db.marketing_livehost_scripts.find_one({'id': script_id}, {'_id': 0})
    if not script:
        raise HTTPException(404, 'Script tidak ditemukan')
    
    update_data = {
        'title': data.title,
        'category': data.category,
        'account_id': data.account_id,
        'script_text': data.script_text,
        'language': data.language,
        'products_applicable': data.products_applicable or [],
        'updated_at': _now(),
    }
    
    await db.marketing_livehost_scripts.update_one({'id': script_id}, {'$set': update_data})
    
    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'update', 'marketing_livehost_script',
        f"Updated script: {data.title}"
    )
    
    return serialize_doc({'message': 'Script berhasil diupdate'})


@router.delete('/scripts/{script_id}')
async def delete_script(script_id: str, request: Request):
    """Admin deletes script (soft delete)"""
    await require_auth(request)
    db = get_db()
    
    script = await db.marketing_livehost_scripts.find_one({'id': script_id}, {'_id': 0})
    if not script:
        raise HTTPException(404, 'Script tidak ditemukan')
    
    await db.marketing_livehost_scripts.update_one(
        {'id': script_id},
        {'$set': {'is_active': False, 'updated_at': _now()}}
    )
    
    return serialize_doc({'message': 'Script berhasil dihapus'})


# ══════════════════════════════════════════════════════════════════════════════
# TRAINING MODULES
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/training')
async def create_training(data: TrainingCreate, request: Request):
    """Admin creates a training module"""
    await require_auth(request)
    db = get_db()
    
    training = {
        'id': _uid(),
        'title': data.title,
        'category': data.category,
        'description': data.description,
        'content_type': data.content_type,
        'content_url': data.content_url or '',
        'duration_minutes': data.duration_minutes,
        'is_required': data.is_required,
        'expiry_months': data.expiry_months,
        'passing_score': data.passing_score,
        'is_active': True,
        'created_at': _now(),
        'created_by': _get_user(request).get('email', 'system'),
    }
    
    await db.marketing_livehost_training.insert_one(training)
    
    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'create', 'marketing_livehost_training',
        f"Created training: {data.title}"
    )
    
    return serialize_doc({'message': 'Training berhasil dibuat', 'training': training})


@router.get('/training')
async def list_training(
    request: Request,
    category: Optional[str] = Query(None),
    is_required: Optional[bool] = Query(None),
):
    """Admin lists all training modules"""
    await require_auth(request)
    db = get_db()
    
    query = {'is_active': True}
    if category:
        query['category'] = category
    if is_required is not None:
        query['is_required'] = is_required
    
    trainings = await db.marketing_livehost_training.find(
        query, {'_id': 0}
    ).sort('created_at', -1).to_list(500)
    
    return serialize_doc(trainings)


@router.put('/training/{training_id}')
async def update_training(training_id: str, data: TrainingCreate, request: Request):
    """Admin updates training module"""
    await require_auth(request)
    db = get_db()
    
    training = await db.marketing_livehost_training.find_one({'id': training_id}, {'_id': 0})
    if not training:
        raise HTTPException(404, 'Training tidak ditemukan')
    
    update_data = {
        'title': data.title,
        'category': data.category,
        'description': data.description,
        'content_type': data.content_type,
        'content_url': data.content_url or training.get('content_url', ''),
        'duration_minutes': data.duration_minutes,
        'is_required': data.is_required,
        'expiry_months': data.expiry_months,
        'passing_score': data.passing_score,
        'updated_at': _now(),
    }
    
    await db.marketing_livehost_training.update_one({'id': training_id}, {'$set': update_data})
    
    return serialize_doc({'message': 'Training berhasil diupdate'})


@router.delete('/training/{training_id}')
async def delete_training(training_id: str, request: Request):
    """Admin deletes training (soft delete)"""
    await require_auth(request)
    db = get_db()
    
    training = await db.marketing_livehost_training.find_one({'id': training_id}, {'_id': 0})
    if not training:
        raise HTTPException(404, 'Training tidak ditemukan')
    
    await db.marketing_livehost_training.update_one(
        {'id': training_id},
        {'$set': {'is_active': False, 'updated_at': _now()}}
    )
    
    return serialize_doc({'message': 'Training berhasil dihapus'})


# ══════════════════════════════════════════════════════════════════════════════
# TRAINING ASSIGNMENT & PROGRESS
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/training/assign')
async def assign_training(data: TrainingAssign, request: Request):
    """Admin assigns training to LiveHosts"""
    await require_auth(request)
    db = get_db()
    
    # Validate training exists
    training = await db.marketing_livehost_training.find_one({'id': data.training_id}, {'_id': 0})
    if not training:
        raise HTTPException(404, 'Training tidak ditemukan')
    
    # Validate hosts exist
    hosts = await db.marketing_livehosts.find(
        {'id': {'$in': data.host_ids}}, {'_id': 0, 'id': 1, 'name': 1}
    ).to_list(500)
    
    if len(hosts) != len(data.host_ids):
        raise HTTPException(400, 'Beberapa LiveHost tidak ditemukan')
    
    # Calculate expiry date if training has expiry
    expiry_date = None
    if training.get('expiry_months'):
        from dateutil.relativedelta import relativedelta
        expiry_date = _now() + relativedelta(months=training['expiry_months'])
    
    # Create progress records for each host
    assignments = []
    for host in hosts:
        # Check if already assigned
        existing = await db.marketing_livehost_training_progress.find_one({
            'host_id': host['id'],
            'training_id': data.training_id,
        })
        
        if existing:
            continue  # Skip if already assigned
        
        progress = {
            'id': _uid(),
            'host_id': host['id'],
            'host_name': host['name'],
            'training_id': data.training_id,
            'training_title': training['title'],
            'status': 'not_started',  # not_started | in_progress | completed
            'score': None,
            'started_at': None,
            'completed_at': None,
            'expiry_date': expiry_date,
            'certificate_url': None,
            'assigned_at': _now(),
            'assigned_by': _get_user(request).get('email', 'system'),
        }
        
        await db.marketing_livehost_training_progress.insert_one(progress)
        assignments.append(progress)

        # SSE: notify host about new training assignment
        try:
            await publish_livehost_notification(
                db,
                host_id=host['id'],
                type_='training_assigned',
                severity='info',
                title='Training Baru di-Assign',
                message=f"Anda di-assign training: {training['title']}",
                link='/training',
            )
        except Exception:
            pass
    
    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'create', 'marketing_livehost_training_assignment',
        f"Assigned training '{training['title']}' to {len(assignments)} LiveHost(s)"
    )
    
    return serialize_doc({
        'message': f'Training berhasil di-assign ke {len(assignments)} LiveHost',
        'assignments': len(assignments),
        'skipped': len(data.host_ids) - len(assignments),
    })


@router.get('/training/progress')
async def get_training_progress(
    request: Request,
    host_id: Optional[str] = Query(None),
    training_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """Admin views training progress"""
    await require_auth(request)
    db = get_db()
    
    query = {}
    if host_id:
        query['host_id'] = host_id
    if training_id:
        query['training_id'] = training_id
    if status:
        query['status'] = status
    
    progress_list = await db.marketing_livehost_training_progress.find(
        query, {'_id': 0}
    ).sort('assigned_at', -1).to_list(500)
    
    return serialize_doc(progress_list)


@router.post('/training/progress/{progress_id}/complete')
async def complete_training(progress_id: str, data: TrainingComplete, request: Request):
    """Admin marks training as completed for a LiveHost"""
    await require_auth(request)
    db = get_db()
    
    progress = await db.marketing_livehost_training_progress.find_one({'id': progress_id}, {'_id': 0})
    if not progress:
        raise HTTPException(404, 'Training progress tidak ditemukan')
    
    if progress['status'] == 'completed':
        raise HTTPException(400, 'Training sudah completed sebelumnya')
    
    # Get training details for validation
    training = await db.marketing_livehost_training.find_one({'id': progress['training_id']}, {'_id': 0})
    if not training:
        raise HTTPException(404, 'Training tidak ditemukan')
    
    # Validate passing score if quiz type
    if training.get('passing_score') and data.score is not None:
        if data.score < training['passing_score']:
            raise HTTPException(400, f"Score {data.score} tidak mencapai passing score {training['passing_score']}")
    
    # Calculate new expiry date
    expiry_date = None
    if training.get('expiry_months'):
        from dateutil.relativedelta import relativedelta
        expiry_date = _now() + relativedelta(months=training['expiry_months'])
    
    update_data = {
        'status': 'completed',
        'score': data.score,
        'completed_at': _now(),
        'expiry_date': expiry_date,
    }
    
    await db.marketing_livehost_training_progress.update_one({'id': progress_id}, {'$set': update_data})
    
    # Update host's training_completed list
    await db.marketing_livehosts.update_one(
        {'id': progress['host_id']},
        {'$addToSet': {'training_completed': progress['training_id']}}
    )
    
    return serialize_doc({'message': 'Training berhasil di-mark as completed'})


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3: ANALYTICS & PAYMENT CALCULATION
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/analytics/host-performance')
async def get_host_performance(
    request: Request,
    month: Optional[str] = Query(None, description="YYYY-MM"),
    host_id: Optional[str] = Query(None),
):
    """Admin views LiveHost performance analytics"""
    await require_auth(request)
    db = get_db()
    
    # Default to current month if not specified
    if not month:
        month = _now().strftime('%Y-%m')
    
    year, mon = month.split('-')
    date_from = f"{year}-{mon}-01"
    
    # Calculate last day of month
    import calendar
    last_day = calendar.monthrange(int(year), int(mon))[1]
    date_to = f"{year}-{mon}-{last_day}"
    
    # Build query
    query = {
        'date': {'$gte': date_from, '$lte': date_to},
        'attendance_status': 'completed'
    }
    if host_id:
        query['host_id'] = host_id
    
    shifts = await db.marketing_livehost_shifts.find(query, {'_id': 0}).to_list(5000)
    
    # Aggregate by host
    host_stats = {}
    for shift in shifts:
        hid = shift['host_id']
        if hid not in host_stats:
            host_stats[hid] = {
                'host_id': hid,
                'host_name': shift['host_name'],
                'total_shifts': 0,
                'total_hours': 0,
                'total_revenue': 0,
                'total_orders': 0,
                'total_viewers': 0,
                'avg_revenue_per_shift': 0,
                'avg_viewers_per_shift': 0,
                'best_shift_revenue': 0,
                'best_shift_date': None,
            }
        
        stats = host_stats[hid]
        stats['total_shifts'] += 1
        stats['total_hours'] += (shift.get('actual_duration_minutes') or 0) / 60
        stats['total_revenue'] += shift.get('revenue', 0)
        stats['total_orders'] += shift.get('orders', 0)
        stats['total_viewers'] += shift.get('viewers', 0)
        
        # Track best shift
        if shift.get('revenue', 0) > stats['best_shift_revenue']:
            stats['best_shift_revenue'] = shift['revenue']
            stats['best_shift_date'] = shift['date']
    
    # Calculate averages
    for stats in host_stats.values():
        if stats['total_shifts'] > 0:
            stats['avg_revenue_per_shift'] = stats['total_revenue'] / stats['total_shifts']
            stats['avg_viewers_per_shift'] = stats['total_viewers'] / stats['total_shifts']
            stats['avg_orders_per_shift'] = stats['total_orders'] / stats['total_shifts']
    
    # Sort by total revenue descending
    performance_list = sorted(host_stats.values(), key=lambda x: x['total_revenue'], reverse=True)
    
    return serialize_doc({
        'month': month,
        'date_range': {'from': date_from, 'to': date_to},
        'total_hosts': len(performance_list),
        'performance': performance_list,
    })


@router.get('/analytics/shift-analysis')
async def get_shift_analysis(
    request: Request,
    month: Optional[str] = Query(None, description="YYYY-MM"),
):
    """Admin views shift time analysis (best performing shift times)"""
    await require_auth(request)
    db = get_db()
    
    # Default to current month
    if not month:
        month = _now().strftime('%Y-%m')
    
    year, mon = month.split('-')
    date_from = f"{year}-{mon}-01"
    import calendar
    last_day = calendar.monthrange(int(year), int(mon))[1]
    date_to = f"{year}-{mon}-{last_day}"
    
    shifts = await db.marketing_livehost_shifts.find({
        'date': {'$gte': date_from, '$lte': date_to},
        'attendance_status': 'completed',
        'revenue': {'$gt': 0}
    }, {'_id': 0}).to_list(5000)
    
    # Analyze by shift type
    shift_type_stats = {}
    for shift in shifts:
        stype = shift.get('shift_type', 'unknown')
        if stype not in shift_type_stats:
            shift_type_stats[stype] = {
                'shift_type': stype,
                'count': 0,
                'total_revenue': 0,
                'total_viewers': 0,
                'avg_revenue': 0,
                'avg_viewers': 0,
            }
        
        stats = shift_type_stats[stype]
        stats['count'] += 1
        stats['total_revenue'] += shift.get('revenue', 0)
        stats['total_viewers'] += shift.get('viewers', 0)
    
    # Calculate averages
    for stats in shift_type_stats.values():
        if stats['count'] > 0:
            stats['avg_revenue'] = stats['total_revenue'] / stats['count']
            stats['avg_viewers'] = stats['total_viewers'] / stats['count']
    
    # Analyze by day of week
    from datetime import datetime
    day_stats = {}
    for shift in shifts:
        try:
            date_obj = datetime.fromisoformat(shift['date'])
            day_name = date_obj.strftime('%A')
            
            if day_name not in day_stats:
                day_stats[day_name] = {
                    'day': day_name,
                    'count': 0,
                    'total_revenue': 0,
                    'avg_revenue': 0,
                }
            
            day_stats[day_name]['count'] += 1
            day_stats[day_name]['total_revenue'] += shift.get('revenue', 0)
        except:
            pass
    
    # Calculate averages for days
    for stats in day_stats.values():
        if stats['count'] > 0:
            stats['avg_revenue'] = stats['total_revenue'] / stats['count']
    
    # Sort
    shift_type_list = sorted(shift_type_stats.values(), key=lambda x: x['avg_revenue'], reverse=True)
    day_list = sorted(day_stats.values(), key=lambda x: x['avg_revenue'], reverse=True)
    
    return serialize_doc({
        'month': month,
        'by_shift_type': shift_type_list,
        'by_day_of_week': day_list,
    })


# ══════════════════════════════════════════════════════════════════════════════
# PAYMENT CALCULATION & SYNC TO FINANCE
# ══════════════════════════════════════════════════════════════════════════════

@router.post('/payment/calculate')
async def calculate_payments(
    request: Request,
    month: str = Query(..., description="YYYY-MM"),
):
    """Admin calculates payment for all completed shifts in a month"""
    await require_auth(request)
    db = get_db()
    
    year, mon = month.split('-')
    date_from = f"{year}-{mon}-01"
    import calendar
    last_day = calendar.monthrange(int(year), int(mon))[1]
    date_to = f"{year}-{mon}-{last_day}"
    
    # Get all completed shifts that haven't been calculated yet
    shifts = await db.marketing_livehost_shifts.find({
        'date': {'$gte': date_from, '$lte': date_to},
        'attendance_status': 'completed',
        'payment_status': {'$in': ['pending', None]}
    }, {'_id': 0}).to_list(5000)
    
    if not shifts:
        return serialize_doc({'message': 'Tidak ada shift yang perlu dihitung', 'calculated': 0})
    
    # Get hosts data for hourly rates
    host_ids = list(set(s['host_id'] for s in shifts))
    hosts = await db.marketing_livehosts.find(
        {'id': {'$in': host_ids}}, {'_id': 0, 'id': 1, 'hourly_rate': 1}
    ).to_list(500)
    host_rates = {h['id']: h.get('hourly_rate', 0) for h in hosts}
    
    calculated_count = 0
    for shift in shifts:
        host_id = shift['host_id']
        hourly_rate = host_rates.get(host_id, 0)
        
        # Calculate base pay (hours * hourly_rate)
        actual_hours = (shift.get('actual_duration_minutes') or 0) / 60
        base_pay = actual_hours * hourly_rate
        
        # Calculate bonus (simple: 10% of revenue if revenue > 5M)
        bonus = 0
        revenue = shift.get('revenue', 0)
        if revenue > 5000000:
            bonus = revenue * 0.10
        
        # Calculate penalty (late = -50k)
        penalty = 0
        if shift.get('attendance_status') == 'late':
            penalty = 50000
        
        # Total pay
        total_pay = base_pay + bonus - penalty
        
        # Update shift
        await db.marketing_livehost_shifts.update_one(
            {'id': shift['id']},
            {'$set': {
                'base_pay': base_pay,
                'bonus': bonus,
                'penalty': penalty,
                'total_pay': total_pay,
                'payment_status': 'calculated',
                'calculated_at': _now(),
                'calculated_by': _get_user(request).get('email', 'system'),
            }}
        )
        calculated_count += 1
    
    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'create', 'marketing_livehost_payment_calculation',
        f"Calculated payment for {calculated_count} shifts in {month}"
    )
    
    return serialize_doc({
        'message': f'Payment berhasil dihitung untuk {calculated_count} shift',
        'calculated': calculated_count,
        'month': month,
    })


@router.post('/payment/sync-to-finance')
async def sync_payments_to_finance(
    request: Request,
    month: str = Query(..., description="YYYY-MM"),
):
    """Admin syncs calculated payments to Finance/Payroll module"""
    await require_auth(request)
    db = get_db()
    
    year, mon = month.split('-')
    date_from = f"{year}-{mon}-01"
    import calendar
    last_day = calendar.monthrange(int(year), int(mon))[1]
    date_to = f"{year}-{mon}-{last_day}"
    
    # Get all calculated shifts that haven't been synced
    shifts = await db.marketing_livehost_shifts.find({
        'date': {'$gte': date_from, '$lte': date_to},
        'payment_status': 'calculated'
    }, {'_id': 0}).to_list(5000)
    
    if not shifts:
        return serialize_doc({'message': 'Tidak ada payment yang perlu di-sync', 'synced': 0})
    
    # Aggregate by host
    host_payments = {}
    for shift in shifts:
        host_id = shift['host_id']
        if host_id not in host_payments:
            host_payments[host_id] = {
                'host_id': host_id,
                'host_name': shift['host_name'],
                'shifts': [],
                'total_base_pay': 0,
                'total_bonus': 0,
                'total_penalty': 0,
                'total_payment': 0,
            }
        
        hp = host_payments[host_id]
        hp['shifts'].append({
            'shift_id': shift['id'],
            'date': shift['date'],
            'base_pay': shift.get('base_pay', 0),
            'bonus': shift.get('bonus', 0),
            'penalty': shift.get('penalty', 0),
            'total': shift.get('total_pay', 0),
        })
        hp['total_base_pay'] += shift.get('base_pay', 0)
        hp['total_bonus'] += shift.get('bonus', 0)
        hp['total_penalty'] += shift.get('penalty', 0)
        hp['total_payment'] += shift.get('total_pay', 0)
    
    # Create payroll entries (sync to Finance module)
    # Assuming Finance module has a collection: payroll_entries
    synced_count = 0
    for host_id, payment_data in host_payments.items():
        payroll_entry = {
            'id': _uid(),
            'type': 'livehost_payment',
            'month': month,
            'employee_id': host_id,
            'employee_name': payment_data['host_name'],
            'employee_type': 'livehost',  # Distinguish from regular employees
            'base_salary': payment_data['total_base_pay'],
            'bonuses': payment_data['total_bonus'],
            'deductions': payment_data['total_penalty'],
            'net_salary': payment_data['total_payment'],
            'shifts_detail': payment_data['shifts'],
            'status': 'pending_approval',  # Finance needs to approve
            'created_at': _now(),
            'created_by': _get_user(request).get('email', 'system'),
            'source_module': 'marketing_livehost',
        }
        
        await db.payroll_entries.insert_one(payroll_entry)
        synced_count += 1

        # SSE: notify host their payment was synced to finance
        try:
            await publish_livehost_notification(
                db,
                host_id=host_id,
                type_='payment_synced',
                severity='success',
                title='Pembayaran Disinkronisasi ke Finance',
                message=f"Pembayaran bulan {month} (Rp {payment_data['total_payment']:,.0f}) telah dikirim ke Finance untuk persetujuan",
                link='/payments',
            )
        except Exception:
            pass
    
    # Mark shifts as synced
    shift_ids = [s['id'] for s in shifts]
    await db.marketing_livehost_shifts.update_many(
        {'id': {'$in': shift_ids}},
        {'$set': {
            'payment_status': 'synced_to_finance',
            'synced_at': _now(),
            'synced_by': _get_user(request).get('email', 'system'),
        }}
    )
    
    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'create', 'marketing_livehost_payment_sync',
        f"Synced payment for {synced_count} LiveHosts ({len(shifts)} shifts) in {month} to Finance"
    )
    
    return serialize_doc({
        'message': f'Payment berhasil di-sync ke Finance untuk {synced_count} LiveHost',
        'synced_hosts': synced_count,
        'synced_shifts': len(shifts),
        'month': month,
    })


@router.get('/payment/status')
async def get_payment_status(
    request: Request,
    month: str = Query(..., description="YYYY-MM"),
):
    """Admin views payment status summary for a month"""
    await require_auth(request)
    db = get_db()
    
    year, mon = month.split('-')
    date_from = f"{year}-{mon}-01"
    import calendar
    last_day = calendar.monthrange(int(year), int(mon))[1]
    date_to = f"{year}-{mon}-{last_day}"
    
    # Aggregate shifts by payment status
    pipeline = [
        {'$match': {
            'date': {'$gte': date_from, '$lte': date_to},
            'attendance_status': 'completed'
        }},
        {'$group': {
            '_id': '$payment_status',
            'count': {'$sum': 1},
            'total_pay': {'$sum': '$total_pay'}
        }}
    ]
    
    results = await db.marketing_livehost_shifts.aggregate(pipeline).to_list(100)
    
    status_summary = {
        'pending': {'count': 0, 'total_pay': 0},
        'calculated': {'count': 0, 'total_pay': 0},
        'synced_to_finance': {'count': 0, 'total_pay': 0},
    }
    
    for result in results:
        status = result['_id'] or 'pending'
        if status in status_summary:
            status_summary[status] = {
                'count': result['count'],
                'total_pay': result['total_pay']
            }
    
    return serialize_doc({
        'month': month,
        'status_summary': status_summary,
        'total_completed_shifts': sum(s['count'] for s in status_summary.values()),
        'total_amount': sum(s['total_pay'] for s in status_summary.values()),
    })


# ══════════════════════════════════════════════════════════════════════════════
# SOP DOCUMENT (PDF) — ADMIN ONLY
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/sop/download')
async def download_livehost_sop(request: Request):
    """
    Download the LiveHost Management SOP as a PDF document.
    Accessible to authenticated admin users.
    """
    await require_auth(request)
    from fastapi.responses import Response
    from utils.livehost_sop_pdf import build_livehost_sop_pdf

    pdf_bytes = build_livehost_sop_pdf(company_name='CV. DEWI ADITYA OFFICIAL')
    filename = f'SOP_LiveHost_v1.0_{_now().strftime("%Y%m%d")}.pdf'
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 4: LIVEHOST PORTAL (Separate Portal for LiveHost)
# ══════════════════════════════════════════════════════════════════════════════

# Brute-force protection for portal login
PORTAL_LOGIN_ATTEMPTS = {}  # {identifier: {'attempts': count, 'locked_until': datetime}}

class LiveHostLoginAttempt(BaseModel):
    email: str
    password: str


@router.post('/portal/auth/login')
async def livehost_portal_login(data: LiveHostLoginAttempt, request: Request):
    """LiveHost login to their portal (separate from admin)"""
    db = get_db()
    
    # Brute-force protection
    client_ip = request.client.host if request.client else 'unknown'
    identifier = f"{client_ip}:{data.email.lower()}"
    
    # Check if locked
    if identifier in PORTAL_LOGIN_ATTEMPTS:
        attempt_data = PORTAL_LOGIN_ATTEMPTS[identifier]
        if attempt_data.get('locked_until') and _now() < attempt_data['locked_until']:
            remaining = int((attempt_data['locked_until'] - _now()).total_seconds() / 60)
            raise HTTPException(429, f'Terlalu banyak percobaan gagal. Coba lagi dalam {remaining} menit')
    
    # Find host
    host = await db.marketing_livehosts.find_one({'email': data.email.lower().strip()}, {'_id': 0})
    if not host or host.get('status') != 'active':
        # Track failed attempt
        if identifier not in PORTAL_LOGIN_ATTEMPTS:
            PORTAL_LOGIN_ATTEMPTS[identifier] = {'attempts': 0, 'first_attempt': _now()}
        PORTAL_LOGIN_ATTEMPTS[identifier]['attempts'] += 1
        PORTAL_LOGIN_ATTEMPTS[identifier]['last_attempt'] = _now()
        
        # Lock after 5 failed attempts
        if PORTAL_LOGIN_ATTEMPTS[identifier]['attempts'] >= 5:
            PORTAL_LOGIN_ATTEMPTS[identifier]['locked_until'] = _now() + timedelta(minutes=15)
        
        raise HTTPException(401, 'Email atau password salah')
    
    # Verify password
    if not verify_password(data.password, host.get('password_hash', '')):
        # Track failed attempt
        if identifier not in PORTAL_LOGIN_ATTEMPTS:
            PORTAL_LOGIN_ATTEMPTS[identifier] = {'attempts': 0, 'first_attempt': _now()}
        PORTAL_LOGIN_ATTEMPTS[identifier]['attempts'] += 1
        PORTAL_LOGIN_ATTEMPTS[identifier]['last_attempt'] = _now()
        
        if PORTAL_LOGIN_ATTEMPTS[identifier]['attempts'] >= 5:
            PORTAL_LOGIN_ATTEMPTS[identifier]['locked_until'] = _now() + timedelta(minutes=15)
        
        raise HTTPException(401, 'Email atau password salah')
    
    # Success - clear attempts
    if identifier in PORTAL_LOGIN_ATTEMPTS:
        del PORTAL_LOGIN_ATTEMPTS[identifier]
    
    # Update last login
    await db.marketing_livehosts.update_one(
        {'id': host['id']},
        {'$set': {'last_login_at': _now()}}
    )
    
    # Create token
    token = _create_livehost_token(host)
    
    return serialize_doc({
        'token': token,
        'host': {
            'id': host['id'],
            'name': host['name'],
            'email': host['email'],
            'phone': host.get('phone', ''),
            'employment_type': host.get('employment_type', ''),
        }
    })


@router.get('/portal/my-profile')
async def get_my_profile(request: Request):
    """LiveHost views their own profile"""
    host = await require_livehost_auth(request)
    db = get_db()
    
    # Get full profile
    full_host = await db.marketing_livehosts.find_one({'id': host['id']}, {'_id': 0, 'password_hash': 0})
    if not full_host:
        raise HTTPException(404, 'Profile tidak ditemukan')
    
    # Get assigned accounts detail
    if full_host.get('assigned_account_ids'):
        accounts = await db.marketing_platform_accounts.find(
            {'id': {'$in': full_host['assigned_account_ids']}}, {'_id': 0}
        ).to_list(100)
        full_host['assigned_accounts'] = accounts
    else:
        full_host['assigned_accounts'] = []
    
    return serialize_doc(full_host)


@router.get('/portal/my-shifts')
async def get_my_shifts(
    request: Request,
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    status: Optional[str] = Query(None),
):
    """LiveHost views their own shifts"""
    host = await require_livehost_auth(request)
    db = get_db()
    
    # Default to current month if not specified
    if not date_from:
        date_from = _now().strftime('%Y-%m-01')
    if not date_to:
        # Last day of current month
        import calendar
        now = _now()
        last_day = calendar.monthrange(now.year, now.month)[1]
        date_to = now.strftime(f'%Y-%m-{last_day}')
    
    query = {
        'host_id': host['id'],
        'date': {'$gte': date_from, '$lte': date_to}
    }
    if status:
        query['attendance_status'] = status
    
    shifts = await db.marketing_livehost_shifts.find(
        query, {'_id': 0}
    ).sort('date', -1).to_list(500)
    
    return serialize_doc({
        'shifts': shifts,
        'date_range': {'from': date_from, 'to': date_to},
        'total': len(shifts),
    })


@router.get('/portal/scripts')
async def get_my_scripts(request: Request):
    """LiveHost views available scripts"""
    host = await require_livehost_auth(request)
    db = get_db()
    
    # Get scripts that are either global or specific to assigned accounts
    query = {
        'is_active': True,
        '$or': [
            {'account_id': None},  # Global scripts
            {'account_id': {'$in': host.get('assigned_account_ids', [])}}  # Account-specific
        ]
    }
    
    scripts = await db.marketing_livehost_scripts.find(
        query, {'_id': 0}
    ).sort('category', 1).to_list(500)
    
    return serialize_doc(scripts)


@router.get('/portal/training')
async def get_my_training(request: Request):
    """LiveHost views their training assignments and progress"""
    host = await require_livehost_auth(request)
    db = get_db()
    
    # Get training progress
    progress_list = await db.marketing_livehost_training_progress.find(
        {'host_id': host['id']}, {'_id': 0}
    ).sort('assigned_at', -1).to_list(500)
    
    # Enrich with training details
    if progress_list:
        training_ids = list(set(p['training_id'] for p in progress_list))
        trainings = await db.marketing_livehost_training.find(
            {'id': {'$in': training_ids}}, {'_id': 0}
        ).to_list(500)
        training_map = {t['id']: t for t in trainings}
        
        for progress in progress_list:
            training = training_map.get(progress['training_id'])
            if training:
                progress['training_detail'] = training
    
    return serialize_doc(progress_list)


@router.post('/portal/training/{progress_id}/complete')
async def portal_complete_training(progress_id: str, request: Request):
    """LiveHost self-marks their training as completed (no admin needed)"""
    host = await require_livehost_auth(request)
    db = get_db()

    progress = await db.marketing_livehost_training_progress.find_one(
        {'id': progress_id, 'host_id': host['id']}, {'_id': 0}
    )
    if not progress:
        raise HTTPException(404, 'Training progress tidak ditemukan atau bukan milik Anda')

    if progress['status'] == 'completed':
        return {'message': 'Training sudah completed', 'already_completed': True}

    training = await db.marketing_livehost_training.find_one(
        {'id': progress['training_id']}, {'_id': 0}
    )
    if not training:
        raise HTTPException(404, 'Training tidak ditemukan')

    # Calculate new expiry date if training has expiry
    expiry_date = None
    if training.get('expiry_months'):
        from dateutil.relativedelta import relativedelta
        expiry_date = _now() + relativedelta(months=training['expiry_months'])

    update_data = {
        'status': 'completed',
        'completed_at': _now(),
        'expiry_date': expiry_date,
        'self_completed': True,
    }

    await db.marketing_livehost_training_progress.update_one(
        {'id': progress_id}, {'$set': update_data}
    )

    # Add to host's training_completed list
    await db.marketing_livehosts.update_one(
        {'id': host['id']},
        {'$addToSet': {'training_completed': progress['training_id']}}
    )

    return {'message': 'Training berhasil di-mark sebagai selesai'}


@router.post('/portal/clock')
async def portal_clock_in_out(data: ClockInOut, request: Request):
    """LiveHost clocks in/out from portal"""
    host = await require_livehost_auth(request)
    db = get_db()
    
    shift = await db.marketing_livehost_shifts.find_one({'id': data.shift_id}, {'_id': 0})
    if not shift:
        raise HTTPException(404, 'Shift tidak ditemukan')
    
    # Verify shift belongs to this host
    if shift['host_id'] != host['id']:
        raise HTTPException(403, 'Shift ini bukan milik Anda')
    
    now = _now()
    
    if data.action == 'clock_in':
        if shift.get('clock_in_time'):
            raise HTTPException(400, 'Shift sudah di-clock in')
        
        # Determine attendance status
        shift_date_str = shift['date']
        shift_start_str = shift['shift_start_time']
        scheduled_datetime_str = f"{shift_date_str}T{shift_start_str}:00+00:00"
        try:
            scheduled_datetime = datetime.fromisoformat(scheduled_datetime_str.replace('+00:00', '')).replace(tzinfo=timezone.utc)
            time_diff = (now - scheduled_datetime).total_seconds() / 60
            if time_diff > 15:
                attendance_status = 'late'
            else:
                attendance_status = 'on_time'
        except:
            attendance_status = 'on_time'
        
        update_data = {
            'clock_in_time': now,
            'attendance_status': attendance_status,
        }
        
        await db.marketing_livehost_shifts.update_one({'id': data.shift_id}, {'$set': update_data})
        
        return serialize_doc({
            'message': f"Clock in berhasil ({attendance_status})",
            'clock_in_time': now,
            'attendance_status': attendance_status,
        })
    
    elif data.action == 'clock_out':
        if not shift.get('clock_in_time'):
            raise HTTPException(400, 'Shift belum di-clock in')
        if shift.get('clock_out_time'):
            raise HTTPException(400, 'Shift sudah di-clock out')
        
        clock_in_time = shift['clock_in_time']
        if clock_in_time.tzinfo is None:
            clock_in_time = clock_in_time.replace(tzinfo=timezone.utc)
        
        actual_duration_minutes = int((now - clock_in_time).total_seconds() / 60)
        
        update_data = {
            'clock_out_time': now,
            'actual_duration_minutes': actual_duration_minutes,
            'attendance_status': 'completed',
        }
        
        await db.marketing_livehost_shifts.update_one({'id': data.shift_id}, {'$set': update_data})
        
        return serialize_doc({
            'message': 'Clock out berhasil',
            'clock_out_time': now,
            'actual_duration_minutes': actual_duration_minutes,
        })
    
    else:
        raise HTTPException(400, 'Action harus clock_in atau clock_out')


# ══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET NOTIFICATIONS (OPTIONAL - Basic Implementation)
# Note: For full WebSocket, use dedicated WebSocket server or Socket.IO
# This is a simple notification endpoint that can be polled
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/portal/notifications')
async def get_my_notifications(request: Request):
    """LiveHost gets their notifications (polling-based fallback for SSE)"""
    host = await require_livehost_auth(request)
    db = get_db()

    # 1. Persisted notifications (created via publish helper)
    persisted = await db.marketing_livehost_notifications.find(
        {'host_id': host['id']},
        {'_id': 0}
    ).sort('created_at', -1).limit(50).to_list(50)

    # 2. Derived notifications (legacy fallback for backwards compatibility)
    seven_days_ago = (_now() - timedelta(days=7)).strftime('%Y-%m-%d')

    recent_shifts = await db.marketing_livehost_shifts.find({
        'host_id': host['id'],
        'date': {'$gte': seven_days_ago},
        'created_at': {'$gte': _now() - timedelta(days=7)}
    }, {'_id': 0, 'id': 1, 'date': 1, 'shift_type': 1, 'account_name': 1, 'created_at': 1}).sort('created_at', -1).limit(10).to_list(10)

    recent_training = await db.marketing_livehost_training_progress.find({
        'host_id': host['id'],
        'assigned_at': {'$gte': _now() - timedelta(days=7)}
    }, {'_id': 0, 'training_title': 1, 'assigned_at': 1}).sort('assigned_at', -1).limit(10).to_list(10)

    derived = []
    for shift in recent_shifts:
        derived.append({
            'id': f"derived-shift-{shift['id']}",
            'type': 'shift_assigned',
            'title': 'Shift Baru Assigned',
            'message': f"Anda dijadwalkan untuk shift {shift['shift_type']} pada {shift['date']} di {shift.get('account_name', 'Account')}",
            'created_at': shift['created_at'].isoformat() if hasattr(shift['created_at'], 'isoformat') else str(shift['created_at']),
            'link': f"/shifts/{shift['id']}",
            'read': False,
        })
    for training in recent_training:
        derived.append({
            'id': f"derived-training-{training.get('training_title', 'x')}",
            'type': 'training_assigned',
            'title': 'Training Baru',
            'message': f"Anda di-assign training: {training['training_title']}",
            'created_at': training['assigned_at'].isoformat() if hasattr(training['assigned_at'], 'isoformat') else str(training['assigned_at']),
            'link': '/training',
            'read': False,
        })

    # Merge & sort
    all_notifications = list(persisted) + derived
    all_notifications.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    unread_count = sum(1 for n in all_notifications if not n.get('read'))

    return serialize_doc({
        'notifications': all_notifications[:50],
        'unread_count': unread_count,
    })


# ══════════════════════════════════════════════════════════════════════════════
# LIVEHOST PORTAL — SSE REAL-TIME NOTIFICATIONS
# Pattern consistent with /api/notifications/stream (rahaza_notifications.py)
# ══════════════════════════════════════════════════════════════════════════════

# In-memory subscriber registry: host_id → asyncio.Queue
_livehost_sse_subscribers: dict = {}


async def publish_livehost_notification(
    db,
    *,
    host_id: str,
    type_: str,
    title: str,
    message: str,
    severity: str = 'info',
    link: Optional[str] = None,
):
    """
    Persist a LiveHost notification + push to live SSE subscribers.

    Called from: shift creation/update, training assignment, payment sync, etc.
    """
    notif = {
        'id': _uid(),
        'host_id': host_id,
        'type': type_,
        'severity': severity if severity in ('info', 'success', 'warning', 'error') else 'info',
        'title': title,
        'message': message,
        'link': link,
        'read': False,
        'created_at': _now().isoformat(),
    }
    try:
        await db.marketing_livehost_notifications.insert_one(notif.copy())
    except Exception:
        # Non-fatal: failure to persist must not break the originating action
        pass

    # Push to live SSE subscribers for this host
    q = _livehost_sse_subscribers.get(host_id)
    if q is not None:
        try:
            q.put_nowait(notif)
        except Exception:
            pass
    return notif


async def _require_livehost_auth_sse(request: Request) -> dict:
    """
    SSE-compatible auth: accepts Bearer header OR ?token=... query parameter
    (EventSource cannot set custom headers in browsers).
    """
    auth = request.headers.get('Authorization') or request.headers.get('authorization')
    token = None
    if auth and auth.lower().startswith('bearer '):
        token = auth.split(' ', 1)[1].strip()
    if not token:
        token = request.query_params.get('token')
    if not token:
        raise HTTPException(401, 'Tidak ada token')
    payload = _decode_livehost_token(token)
    if not payload:
        raise HTTPException(401, 'Token tidak valid')
    db = get_db()
    host = await db.marketing_livehosts.find_one(
        {'id': payload['sub']}, {'_id': 0, 'password_hash': 0}
    )
    if not host:
        raise HTTPException(401, 'LiveHost tidak ditemukan')
    if host.get('status') != 'active':
        raise HTTPException(403, 'LiveHost tidak aktif')
    return host


@router.get('/portal/notifications/stream')
async def livehost_notifications_stream(request: Request):
    """
    Server-Sent Events stream for LiveHost portal.
    Client connects via EventSource('/api/marketing/livehost/portal/notifications/stream?token=XXX').
    """
    host = await _require_livehost_auth_sse(request)
    host_id = host['id']
    q: asyncio.Queue = asyncio.Queue()
    _livehost_sse_subscribers[host_id] = q

    async def event_generator():
        try:
            yield f"event: ready\ndata: {json.dumps({'subscribed_at': _now().isoformat(), 'host_id': host_id})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    notif = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield f"event: notification\ndata: {json.dumps(notif, default=str)}\n\n"
                except asyncio.TimeoutError:
                    # heartbeat
                    yield "event: ping\ndata: {}\n\n"
        finally:
            # Cleanup on disconnect
            if _livehost_sse_subscribers.get(host_id) is q:
                _livehost_sse_subscribers.pop(host_id, None)

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        }
    )


@router.post('/portal/notifications/{notif_id}/read')
async def mark_notification_read(notif_id: str, request: Request):
    """LiveHost marks notification as read"""
    host = await require_livehost_auth(request)
    db = get_db()
    result = await db.marketing_livehost_notifications.update_one(
        {'id': notif_id, 'host_id': host['id']},
        {'$set': {'read': True, 'read_at': _now().isoformat()}}
    )
    if result.matched_count == 0:
        # Allow marking derived notifications as no-op
        return {'message': 'Notification not found or already read', 'read': True}
    return {'message': 'Notification marked as read', 'read': True}


@router.post('/portal/notifications/mark-all-read')
async def mark_all_notifications_read(request: Request):
    """LiveHost marks all their notifications as read"""
    host = await require_livehost_auth(request)
    db = get_db()
    result = await db.marketing_livehost_notifications.update_many(
        {'host_id': host['id'], 'read': False},
        {'$set': {'read': True, 'read_at': _now().isoformat()}}
    )
    return {'message': 'All notifications marked as read', 'updated': result.modified_count}



# ══════════════════════════════════════════════════════════════════════════════
# DYNAMIC HOST ID ROUTES (MUST be registered LAST to avoid catching
# static segments like /shifts, /scripts, /training, /portal, /payment, /analytics)
# ══════════════════════════════════════════════════════════════════════════════

@router.get('/{host_id}')
async def get_livehost(request: Request, host_id: str = Path(..., regex=UUID_PATH_REGEX)):
    """Admin gets LiveHost detail"""
    await require_auth(request)
    db = get_db()

    host = await db.marketing_livehosts.find_one({'id': host_id}, {'_id': 0, 'password_hash': 0})
    if not host:
        raise HTTPException(404, 'LiveHost tidak ditemukan')

    # Get assigned accounts detail
    if host.get('assigned_account_ids'):
        accounts = await db.marketing_platform_accounts.find(
            {'id': {'$in': host['assigned_account_ids']}}, {'_id': 0}
        ).to_list(500)
        host['assigned_accounts'] = accounts
    else:
        host['assigned_accounts'] = []

    # Get training progress
    progress_list = await db.marketing_livehost_training_progress.find(
        {'host_id': host_id}, {'_id': 0}
    ).to_list(500)
    host['training_progress'] = progress_list

    return serialize_doc(host)


@router.patch('/{host_id}')
async def update_livehost(request: Request, data: LiveHostUpdate, host_id: str = Path(..., regex=UUID_PATH_REGEX)):
    """Admin updates LiveHost"""
    await require_auth(request)
    db = get_db()

    host = await db.marketing_livehosts.find_one({'id': host_id}, {'_id': 0})
    if not host:
        raise HTTPException(404, 'LiveHost tidak ditemukan')

    update_data = {}
    if data.name is not None:
        update_data['name'] = data.name
    if data.email is not None:
        # Check duplicate
        existing = await db.marketing_livehosts.find_one({'email': data.email.lower().strip(), 'id': {'$ne': host_id}})
        if existing:
            raise HTTPException(400, f"Email '{data.email}' sudah digunakan LiveHost lain")
        update_data['email'] = data.email.lower().strip()
    if data.password is not None:
        update_data['password_hash'] = hash_password(data.password)
    if data.phone is not None:
        update_data['phone'] = data.phone
    if data.employment_type is not None:
        update_data['employment_type'] = data.employment_type
    if data.hourly_rate is not None:
        update_data['hourly_rate'] = data.hourly_rate
    if data.shift_preferences is not None:
        update_data['shift_preferences'] = data.shift_preferences
    if data.language_skills is not None:
        update_data['language_skills'] = data.language_skills
    if data.product_expertise is not None:
        update_data['product_expertise'] = data.product_expertise
    if data.assigned_account_ids is not None:
        update_data['assigned_account_ids'] = data.assigned_account_ids
    if data.status is not None:
        update_data['status'] = data.status
    if data.notes is not None:
        update_data['notes'] = data.notes

    update_data['updated_at'] = _now()

    await db.marketing_livehosts.update_one({'id': host_id}, {'$set': update_data})

    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'update', 'marketing_livehost',
        f"Updated LiveHost: {host['name']}"
    )

    updated_host = await db.marketing_livehosts.find_one({'id': host_id}, {'_id': 0, 'password_hash': 0})
    return serialize_doc({'message': 'LiveHost berhasil diupdate', 'host': updated_host})


@router.delete('/{host_id}')
async def delete_livehost(request: Request, host_id: str = Path(..., regex=UUID_PATH_REGEX)):
    """Admin deletes LiveHost (soft delete - set status inactive)"""
    await require_auth(request)
    db = get_db()

    host = await db.marketing_livehosts.find_one({'id': host_id}, {'_id': 0})
    if not host:
        raise HTTPException(404, 'LiveHost tidak ditemukan')

    await db.marketing_livehosts.update_one(
        {'id': host_id},
        {'$set': {'status': 'inactive', 'updated_at': _now()}}
    )

    user = _get_user(request)
    await log_activity(
        user.get('id', 'system'),
        user.get('name') or user.get('email', 'system'),
        'delete', 'marketing_livehost',
        f"Deleted LiveHost: {host['name']}"
    )

    return serialize_doc({'message': 'LiveHost berhasil dihapus (status = inactive)'})
