"""
Notifications — Portal Kolaborasi
Unified in-app notification system: chat mentions, LMS events, document sharing.
Collection: collab_notifications
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from auth import require_auth

router = APIRouter(prefix='/api/collab/notifications', tags=['notifications'])

NOTIF_TYPES = [
    'message',       # New message in channel you're in
    'mention',       # @mention in message
    'document',      # Document shared with you / comment
    'course',        # New course assigned / enrolled
    'assignment',    # Assignment graded / deadline
    'grade',         # Quiz / assignment graded
    'certificate',   # Certificate earned
    'deadline',      # Approaching deadline
    'system',        # System announcement
]

TYPE_ICONS = {
    'message':     '💬',
    'mention':     '@',
    'document':    '📄',
    'course':      '📚',
    'assignment':  '📝',
    'grade':       '⭐',
    'certificate': '🎓',
    'deadline':    '⏰',
    'system':      '🔔',
}


def _ser(doc):
    if not doc:
        return None
    doc = dict(doc)
    doc.pop('_id', None)
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


async def create_notification(
    db,
    user_id: str,
    notif_type: str,
    title: str,
    content: str,
    source_type: str = 'system',
    source_id: str = '',
    source_url: str = '',
    metadata: dict = None,
):
    """Helper called by other route modules to create a notification."""
    now = datetime.now(timezone.utc)
    doc = {
        'notification_id': str(uuid.uuid4()),
        'user_id': user_id,
        'type': notif_type,
        'icon': TYPE_ICONS.get(notif_type, '🔔'),
        'title': title,
        'content': content,
        'source_type': source_type,
        'source_id': source_id,
        'source_url': source_url,
        'metadata': metadata or {},
        'read': False,
        'read_at': None,
        'created_at': now,
    }
    await db.collab_notifications.insert_one(doc)
    return doc


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get('')
async def list_notifications(
    limit: int = Query(30, ge=1, le=100),
    unread_only: bool = Query(False),
    db=Depends(get_db),
    user=Depends(require_auth),
):
    """List notifications for current user."""
    filt = {'user_id': user['id']}
    if unread_only:
        filt['read'] = False

    notifications = await db.collab_notifications.find(
        filt
    ).sort('created_at', -1).to_list(limit)

    unread_count = await db.collab_notifications.count_documents(
        {'user_id': user['id'], 'read': False}
    )

    return {
        'ok': True,
        'notifications': [_ser(n) for n in notifications],
        'unread_count': unread_count,
        'total': len(notifications),
    }


@router.get('/unread-count')
async def get_unread_count(
    db=Depends(get_db),
    user=Depends(require_auth),
):
    """Quick unread count for polling."""
    count = await db.collab_notifications.count_documents(
        {'user_id': user['id'], 'read': False}
    )
    return {'ok': True, 'unread_count': count}


@router.post('/{notification_id}/read')
async def mark_notification_read(
    notification_id: str,
    db=Depends(get_db),
    user=Depends(require_auth),
):
    """Mark a single notification as read."""
    result = await db.collab_notifications.update_one(
        {'notification_id': notification_id, 'user_id': user['id']},
        {'$set': {'read': True, 'read_at': datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail='Notifikasi tidak ditemukan')
    return {'ok': True}


@router.post('/mark-all-read')
async def mark_all_read(
    db=Depends(get_db),
    user=Depends(require_auth),
):
    """Mark all notifications as read."""
    now = datetime.now(timezone.utc)
    result = await db.collab_notifications.update_many(
        {'user_id': user['id'], 'read': False},
        {'$set': {'read': True, 'read_at': now}},
    )
    return {'ok': True, 'updated': result.modified_count}


class CreateNotifRequest(BaseModel):
    notif_type: str = 'system'
    title: str
    content: str
    source_type: str = 'system'
    source_id: str = ''
    source_url: str = ''
    target_user_id: Optional[str] = None
    metadata: dict = {}


@router.post('')
async def create_notification_api(
    body: CreateNotifRequest,
    db=Depends(get_db),
    user=Depends(require_auth),
):
    """Create a notification (admin/system use). Target = self if not specified."""
    target = body.target_user_id or user['id']
    doc = await create_notification(
        db,
        user_id=target,
        notif_type=body.notif_type,
        title=body.title,
        content=body.content,
        source_type=body.source_type,
        source_id=body.source_id,
        source_url=body.source_url,
        metadata=body.metadata,
    )
    return {'ok': True, 'notification': _ser(doc)}


@router.delete('/{notification_id}')
async def delete_notification(
    notification_id: str,
    db=Depends(get_db),
    user=Depends(require_auth),
):
    """Delete a single notification."""
    await db.collab_notifications.delete_one(
        {'notification_id': notification_id, 'user_id': user['id']}
    )
    return {'ok': True}
