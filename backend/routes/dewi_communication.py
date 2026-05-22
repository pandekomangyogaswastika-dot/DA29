"""
CV. Dewi Aditya ERP — Communication Hub (Internal Chat)

Portal komunikasi internal: channel group + direct messages,
real-time via WebSocket, file sharing via storage lokal.

Collections:
  comm_channels         — channel definitions
  comm_messages         — messages (channel + DM)
  comm_conversations    — DM conversation threads (2 participants)
  comm_read_receipts    — unread tracking per user per channel/conv

Endpoints:
  GET    /api/comm/channels                         — list channels user is member of
  POST   /api/comm/channels                         — create channel
  GET    /api/comm/channels/{id}                    — get channel detail
  PUT    /api/comm/channels/{id}                    — update channel (admin/creator)
  POST   /api/comm/channels/{id}/members            — add member(s)
  DELETE /api/comm/channels/{id}/members/{uid}      — remove member
  GET    /api/comm/channels/{id}/messages           — list messages (paginated)
  POST   /api/comm/channels/{id}/messages           — send message to channel
  GET    /api/comm/conversations                    — list DM conversations
  POST   /api/comm/conversations/{uid}/messages     — send DM to user
  GET    /api/comm/conversations/{uid}/messages     — get DM history
  GET    /api/comm/unread                           — unread counts per channel/conv
  POST   /api/comm/read/{channel_id}                — mark channel as read
  POST   /api/comm/messages/{msg_id}/reaction       — add/remove emoji reaction
  POST   /api/comm/channels/{id}/upload             — upload file attachment
  GET    /api/comm/online-users                     — currently online users
  WS     /api/comm/ws?token=                        — WebSocket (real-time)
"""
from fastapi import APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect, Query, UploadFile, File
from fastapi.responses import JSONResponse
from database import get_db
from auth import require_auth, verify_token_str, serialize_doc
from storage import put_object, generate_storage_path
from datetime import datetime, timezone
from typing import Optional, List
from routes.shared import paginated_response
import uuid
import logging
import json
import asyncio
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/comm", tags=["communication-hub"])


def _uid(): return str(uuid.uuid4())
def _now(): return datetime.now(timezone.utc)


def _ser(doc):
    if not doc:
        return doc
    doc = {k: v for k, v in doc.items() if k != '_id'}
    for k, v in doc.items():
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


# ─── WebSocket Connection Manager ─────────────────────────────────────────

class CommConnectionManager:
    """Multi-room WebSocket manager. Each user can have multiple connections (tabs)."""

    def __init__(self):
        # user_id -> list[WebSocket]
        self.connections: dict[str, list] = {}
        # set of online user_ids
        self.online_users: set = set()

    async def connect(self, ws: WebSocket, user_id: str, user_name: str):
        await ws.accept()
        if user_id not in self.connections:
            self.connections[user_id] = []
        self.connections[user_id].append(ws)
        self.online_users.add(user_id)
        logger.info(f"[CommWS] {user_name} connected. Online: {len(self.online_users)}")

    def disconnect(self, ws: WebSocket, user_id: str):
        if user_id in self.connections:
            try:
                self.connections[user_id].remove(ws)
            except ValueError:
                pass
            if not self.connections[user_id]:
                del self.connections[user_id]
                self.online_users.discard(user_id)

    async def send_to_user(self, user_id: str, data: dict):
        if user_id not in self.connections:
            return
        dead = []
        for ws in list(self.connections.get(user_id, [])):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, user_id)

    async def broadcast_to_users(self, user_ids: list, data: dict):
        for uid in user_ids:
            await self.send_to_user(uid, data)

    async def broadcast_presence(self, user_id: str, user_name: str, is_online: bool):
        """Notify all online users about presence change."""
        all_users = list(self.connections.keys())
        payload = {"type": "presence", "data": {"user_id": user_id, "name": user_name, "online": is_online}}
        for uid in all_users:
            if uid != user_id:
                await self.send_to_user(uid, payload)

    def get_online_user_ids(self) -> list:
        return list(self.online_users)


comm_manager = CommConnectionManager()


# ─── Endpoints: Channels ──────────────────────────────────────────────────

@router.get("/channels")
async def list_channels(request: Request, include_archived: bool = False):
    """List channels user is a member of (or all public channels)."""
    user = await require_auth(request)
    db = get_db()
    uid = user["id"]
    # Channels where user is member OR public channels
    base_filter = {"$or": [{"members": uid}, {"type": "public"}]}
    if not include_archived:
        base_filter["archived"] = {"$ne": True}
    else:
        base_filter["archived"] = True
    channels = await db.comm_channels.find(
        base_filter, {"_id": 0}
    ).sort("updated_at", -1).to_list(200)

    # Fetch unread counts
    result = []
    for ch in channels:
        receipt = await db.comm_read_receipts.find_one(
            {"user_id": uid, "ref_id": ch["id"]}, {"_id": 0}
        )
        last_read = receipt.get("last_read_at") if receipt else None
        query = {"channel_id": ch["id"]}
        if last_read:
            query["created_at"] = {"$gt": last_read}
        unread = await db.comm_messages.count_documents(query)
        ch_out = _ser(ch)
        ch_out["unread_count"] = unread
        result.append(ch_out)
    return result


@router.post("/channels")
async def create_channel(request: Request):
    """Create a new channel."""
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "Nama channel wajib diisi.")
    channel_type = body.get("type", "public")  # public | private | department
    members = list(set(body.get("members", []) + [user["id"]]))

    doc = {
        "id": _uid(),
        "name": name,
        "description": (body.get("description") or "").strip(),
        "type": channel_type,
        "members": members,
        "department": body.get("department"),
        "created_by": user["id"],
        "created_by_name": user.get("name", ""),
        "archived": False,
        "created_at": _now(),
        "updated_at": _now(),
        "last_message": None,
        "last_message_at": None,
    }
    await db.comm_channels.insert_one(doc)
    return _ser(doc)


@router.get("/channels/{channel_id}")
async def get_channel(channel_id: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    ch = await db.comm_channels.find_one({"id": channel_id}, {"_id": 0})
    if not ch:
        raise HTTPException(404, "Channel tidak ditemukan.")
    return _ser(ch)


@router.put("/channels/{channel_id}")
async def update_channel(channel_id: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    ch = await db.comm_channels.find_one({"id": channel_id})
    if not ch:
        raise HTTPException(404, "Channel tidak ditemukan.")
    if ch["created_by"] != user["id"] and user.get("role") not in ("superadmin", "admin"):
        raise HTTPException(403, "Hanya pembuat channel atau admin yang bisa mengubah.")
    body = await request.json()
    update = {}
    if "name" in body and body["name"].strip():
        update["name"] = body["name"].strip()
    if "description" in body:
        update["description"] = body["description"].strip()


@router.patch("/channels/{channel_id}/archive")
async def archive_channel(channel_id: str, request: Request):
    """Arsipkan channel. Hanya admin/creator yang bisa."""
    user = await require_auth(request)
    db = get_db()
    ch = await db.comm_channels.find_one({"id": channel_id})
    if not ch:
        raise HTTPException(404, "Channel tidak ditemukan.")
    is_admin = user.get("role") in ("admin", "superadmin")
    is_creator = ch.get("created_by") == user["id"]
    if not (is_admin or is_creator):
        raise HTTPException(403, "Hanya pembuat channel atau admin yang bisa mengarsipkan.")
    if ch.get("archived"):
        raise HTTPException(400, "Channel sudah diarsipkan.")
    await db.comm_channels.update_one(
        {"id": channel_id},
        {"$set": {"archived": True, "archived_at": _now(), "archived_by": user["id"], "updated_at": _now()}}
    )
    return {"ok": True, "archived": True}


@router.patch("/channels/{channel_id}/unarchive")
async def unarchive_channel(channel_id: str, request: Request):
    """Unarsipkan channel."""
    user = await require_auth(request)
    db = get_db()
    ch = await db.comm_channels.find_one({"id": channel_id})
    if not ch:
        raise HTTPException(404, "Channel tidak ditemukan.")
    is_admin = user.get("role") in ("admin", "superadmin")
    is_creator = ch.get("created_by") == user["id"]
    if not (is_admin or is_creator):
        raise HTTPException(403, "Hanya pembuat channel atau admin yang bisa unarchive.")
    await db.comm_channels.update_one(
        {"id": channel_id},
        {"$set": {"archived": False, "archived_at": None, "archived_by": None, "updated_at": _now()}}
    )
    return {"ok": True, "archived": False}
    if "type" in body:
        update["type"] = body["type"]
    if update:
        update["updated_at"] = _now()
        await db.comm_channels.update_one({"id": channel_id}, {"$set": update})
    ch.update(update)
    return _ser(ch)


@router.get("/channels/{channel_id}/members")
async def get_channel_members(channel_id: str, request: Request):
    """Get channel members with display info for @mention autocomplete."""
    user = await require_auth(request)
    db = get_db()
    ch = await db.comm_channels.find_one({"id": channel_id})
    if not ch:
        raise HTTPException(404, "Channel tidak ditemukan.")
    member_ids = ch.get("members", [])
    members_out = []
    for uid in member_ids:
        u = await db.users.find_one({"id": uid})
        if u:
            members_out.append({
                "id": u["id"],
                "name": u.get("name", ""),
                "email": u.get("email", ""),
                "role": u.get("role", ""),
                "department": u.get("department", ""),
                "position": u.get("position", ""),
                "is_self": uid == user["id"],
            })
    return {"members": members_out}


@router.post("/channels/{channel_id}/members")
async def add_channel_members(channel_id: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    ch = await db.comm_channels.find_one({"id": channel_id})
    if not ch:
        raise HTTPException(404, "Channel tidak ditemukan.")
    body = await request.json()
    new_members = body.get("member_ids", [])
    await db.comm_channels.update_one(
        {"id": channel_id},
        {"$addToSet": {"members": {"$each": new_members}}, "$set": {"updated_at": _now()}}
    )
    # Notify new members via WS
    for uid in new_members:
        await comm_manager.send_to_user(uid, {
            "type": "channel_added",
            "data": {"channel_id": channel_id, "channel_name": ch["name"]}
        })
    return {"ok": True, "added": new_members}


@router.delete("/channels/{channel_id}/members/{uid}")
async def remove_channel_member(channel_id: str, uid: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    ch = await db.comm_channels.find_one({"id": channel_id})
    if not ch:
        raise HTTPException(404, "Channel tidak ditemukan.")
    if ch["created_by"] != user["id"] and uid != user["id"] and user.get("role") not in ("superadmin", "admin"):
        raise HTTPException(403, "Tidak diizinkan.")
    await db.comm_channels.update_one(
        {"id": channel_id},
        {"$pull": {"members": uid}, "$set": {"updated_at": _now()}}
    )
    return {"ok": True}


# ─── Endpoints: Channel Messages ─────────────────────────────────────────

@router.get("/channels/{channel_id}/messages")
async def get_channel_messages(
    channel_id: str, request: Request,
    before: Optional[str] = Query(None),  # message_id cursor for pagination
    limit: int = Query(50, ge=1, le=100),
    include_thread_replies: bool = Query(False, description="Include thread replies in main feed (default: hide)"),
):
    await require_auth(request)
    db = get_db()
    ch = await db.comm_channels.find_one({"id": channel_id})
    if not ch:
        raise HTTPException(404, "Channel tidak ditemukan.")
    query = {"channel_id": channel_id, "deleted": {"$ne": True}}
    if not include_thread_replies:
        # Hide messages that are replies in a thread (those have thread_root_id set)
        query["$or"] = [
            {"thread_root_id": {"$exists": False}},
            {"thread_root_id": None},
        ]
    if before:
        anchor = await db.comm_messages.find_one({"id": before})
        if anchor:
            existing_created_at = query.get("created_at", {})
            existing_created_at["$lt"] = anchor["created_at"]
            query["created_at"] = existing_created_at
    msgs = await db.comm_messages.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    msgs.reverse()
    return [_ser(m) for m in msgs]


@router.post("/channels/{channel_id}/messages")
async def send_channel_message(channel_id: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    ch = await db.comm_channels.find_one({"id": channel_id})
    if not ch:
        raise HTTPException(404, "Channel tidak ditemukan.")
    body = await request.json()
    content = (body.get("content") or "").strip()
    if not content and not body.get("file_url"):
        raise HTTPException(400, "Pesan tidak boleh kosong.")
    msg = {
        "id": _uid(),
        "channel_id": channel_id,
        "conversation_id": None,
        "sender_id": user["id"],
        "sender_name": user.get("name", ""),
        "sender_email": user.get("email", ""),
        "content": content,
        "message_type": body.get("message_type", "text"),
        "file_url": body.get("file_url"),
        "file_name": body.get("file_name"),
        "file_size": body.get("file_size"),
        "reply_to_id": body.get("reply_to_id"),
        "reply_to_preview": body.get("reply_to_preview"),
        "reactions": {},
        "edited": False,
        "deleted": False,
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db.comm_messages.insert_one(msg)
    # Update channel last_message
    await db.comm_channels.update_one(
        {"id": channel_id},
        {"$set": {
            "last_message": content or msg["file_name"],
            "last_message_at": _now(),
            "updated_at": _now()
        }}
    )
    msg_out = _ser(msg)
    # Broadcast to all channel members
    members = ch.get("members", [])
    await comm_manager.broadcast_to_users(members, {
        "type": "new_message",
        "data": {"message": msg_out, "channel_id": channel_id, "scope": "channel"}
    })
    # Phase 3.6: Parse @mentions and create notifications
    import re as _re
    mentions = _re.findall(r'@([\w\s\-\.]+?)(?=\s|$|@)', content + ' ')
    if mentions:
        try:
            from routes.notifications import create_notification
            for mention_name in mentions:
                mn = mention_name.strip()
                if not mn:
                    continue
                # Find user by name (case insensitive)
                mentioned_user = await db.users.find_one(
                    {"name": {"$regex": f"^{_re.escape(mn)}$", "$options": "i"}}
                )
                if mentioned_user and mentioned_user["id"] != user["id"]:
                    channel_name = ch.get("name", channel_id)
                    await create_notification(
                        db,
                        user_id=mentioned_user["id"],
                        notif_type="mention",
                        title=f'Anda disebut oleh {user.get("name", "Seseorang")} di #{channel_name}',
                        content=content[:120] + ('...' if len(content) > 120 else ''),
                        source_type="channel",
                        source_id=channel_id,
                        source_url=f"#/comm/channel/{channel_id}",
                        metadata={"channel_name": channel_name, "message_id": msg["id"]},
                    )
        except Exception:
            pass  # Mentions are non-critical
    return msg_out


# ─── Endpoints: Direct Messages ───────────────────────────────────────────

async def _get_or_create_conversation(db, uid1: str, uid2: str) -> dict:
    """Get or create a 1:1 DM conversation between two users."""
    participants = sorted([uid1, uid2])
    conv = await db.comm_conversations.find_one({"participants": participants}, {"_id": 0})
    if not conv:
        conv = {
            "id": _uid(),
            "participants": participants,
            "created_at": _now(),
            "updated_at": _now(),
            "last_message": None,
            "last_message_at": None,
        }
        await db.comm_conversations.insert_one(conv)
    return conv


@router.get("/conversations")
async def list_conversations(request: Request):
    """List all DM conversations for current user."""
    user = await require_auth(request)
    db = get_db()
    uid = user["id"]
    convs = await db.comm_conversations.find(
        {"participants": uid}, {"_id": 0}
    ).sort("updated_at", -1).to_list(100)

    result = []
    for conv in convs:
        # Get the other participant's info
        other_uid = next((p for p in conv["participants"] if p != uid), None)
        other_user = None
        if other_uid:
            other_user = await db.users.find_one({"id": other_uid}, {"_id": 0, "name": 1, "email": 1, "id": 1})
        # Unread count
        receipt = await db.comm_read_receipts.find_one(
            {"user_id": uid, "ref_id": conv["id"]}, {"_id": 0}
        )
        last_read = receipt.get("last_read_at") if receipt else None
        q = {"conversation_id": conv["id"]}
        if last_read:
            q["created_at"] = {"$gt": last_read}
        unread = await db.comm_messages.count_documents(q)

        conv_out = _ser(conv)
        conv_out["other_user"] = _ser(other_user) if other_user else {"id": other_uid, "name": "Unknown"}
        conv_out["unread_count"] = unread
        conv_out["is_online"] = other_uid in comm_manager.online_users
        result.append(conv_out)
    return result


@router.post("/conversations/{other_uid}/messages")
async def send_dm(other_uid: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    content = (body.get("content") or "").strip()
    if not content and not body.get("file_url"):
        raise HTTPException(400, "Pesan tidak boleh kosong.")
    conv = await _get_or_create_conversation(db, user["id"], other_uid)
    msg = {
        "id": _uid(),
        "channel_id": None,
        "conversation_id": conv["id"],
        "sender_id": user["id"],
        "sender_name": user.get("name", ""),
        "sender_email": user.get("email", ""),
        "content": content,
        "message_type": body.get("message_type", "text"),
        "file_url": body.get("file_url"),
        "file_name": body.get("file_name"),
        "file_size": body.get("file_size"),
        "reply_to_id": body.get("reply_to_id"),
        "reply_to_preview": body.get("reply_to_preview"),
        "reactions": {},
        "edited": False,
        "deleted": False,
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db.comm_messages.insert_one(msg)
    await db.comm_conversations.update_one(
        {"id": conv["id"]},
        {"$set": {"last_message": content or msg["file_name"], "last_message_at": _now(), "updated_at": _now()}}
    )
    msg_out = _ser(msg)
    # Notify recipient
    await comm_manager.send_to_user(other_uid, {
        "type": "new_message",
        "data": {"message": msg_out, "conv_id": conv["id"], "scope": "dm"}
    })
    return msg_out


@router.get("/conversations/{other_uid}/messages")
async def get_dm_messages(
    other_uid: str, request: Request,
    before: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    include_thread_replies: bool = Query(False),
):
    user = await require_auth(request)
    db = get_db()
    conv = await _get_or_create_conversation(db, user["id"], other_uid)
    query = {"conversation_id": conv["id"], "deleted": {"$ne": True}}
    if not include_thread_replies:
        query["$or"] = [
            {"thread_root_id": {"$exists": False}},
            {"thread_root_id": None},
        ]
    if before:
        anchor = await db.comm_messages.find_one({"id": before})
        if anchor:
            existing_created_at = query.get("created_at", {})
            existing_created_at["$lt"] = anchor["created_at"]
            query["created_at"] = existing_created_at
    msgs = await db.comm_messages.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    msgs.reverse()
    return [_ser(m) for m in msgs]


# ═══════════════════════════════════════════════════════════════════════════════
# THREAD CONVERSATIONS (Session 28) — Slack-style nested replies
# Data model adds: thread_root_id (on replies) + thread_reply_count, thread_last_reply_at,
# thread_participants (on root messages — denormalized for performance)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/messages/{root_id}/thread")
async def get_thread(root_id: str, request: Request):
    """
    Returns the root message + all its thread replies (oldest → newest).
    """
    user = await require_auth(request)
    db = get_db()

    root = await db.comm_messages.find_one({"id": root_id, "deleted": {"$ne": True}})
    if not root:
        raise HTTPException(404, "Message tidak ditemukan.")

    # Authorization: user must have access to the channel/DM this root belongs to
    if root.get("channel_id"):
        ch = await db.comm_channels.find_one({"id": root["channel_id"]})
        if not ch:
            raise HTTPException(404, "Channel tidak ditemukan.")
        if ch.get("type") != "public" and user["id"] not in (ch.get("members") or []):
            raise HTTPException(403, "Anda bukan anggota channel ini.")
    elif root.get("conversation_id"):
        conv = await db.comm_conversations.find_one({"id": root["conversation_id"]})
        if not conv or user["id"] not in (conv.get("participants") or []):
            raise HTTPException(403, "Anda tidak punya akses ke conversation ini.")

    # Fetch replies
    replies = await db.comm_messages.find(
        {"thread_root_id": root_id, "deleted": {"$ne": True}},
        {"_id": 0}
    ).sort("created_at", 1).to_list(1000)

    return {
        "root": _ser(root),
        "replies": [_ser(r) for r in replies],
        "reply_count": len(replies),
    }


@router.post("/messages/{root_id}/thread/reply")
async def post_thread_reply(root_id: str, request: Request):
    """
    Post a reply inside a thread. The reply inherits the root's channel/conversation scope.
    Updates denormalized thread_reply_count on the root.
    """
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    content = (body.get("content") or "").strip()
    if not content and not body.get("file_url"):
        raise HTTPException(400, "Pesan tidak boleh kosong.")

    root = await db.comm_messages.find_one({"id": root_id, "deleted": {"$ne": True}})
    if not root:
        raise HTTPException(404, "Root message tidak ditemukan.")

    # Authorization check (same as get_thread)
    if root.get("channel_id"):
        ch = await db.comm_channels.find_one({"id": root["channel_id"]})
        if not ch:
            raise HTTPException(404, "Channel tidak ditemukan.")
        if ch.get("type") != "public" and user["id"] not in (ch.get("members") or []):
            raise HTTPException(403, "Anda bukan anggota channel ini.")
    elif root.get("conversation_id"):
        conv = await db.comm_conversations.find_one({"id": root["conversation_id"]})
        if not conv or user["id"] not in (conv.get("participants") or []):
            raise HTTPException(403, "Anda tidak punya akses ke conversation ini.")

    # Prevent threading a thread reply (only root messages can have threads)
    if root.get("thread_root_id"):
        raise HTTPException(400, "Tidak bisa reply pada thread reply. Gunakan root message-nya.")

    reply = {
        "id": _uid(),
        "channel_id": root.get("channel_id"),
        "conversation_id": root.get("conversation_id"),
        "thread_root_id": root_id,
        "sender_id": user["id"],
        "sender_name": user.get("name", ""),
        "sender_email": user.get("email", ""),
        "content": content,
        "message_type": body.get("message_type", "text"),
        "file_url": body.get("file_url"),
        "file_name": body.get("file_name"),
        "file_size": body.get("file_size"),
        "reactions": {},
        "edited": False,
        "deleted": False,
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db.comm_messages.insert_one(reply)

    # Update root denormalized fields
    new_reply_count = (root.get("thread_reply_count") or 0) + 1
    participants = set(root.get("thread_participants") or [])
    participants.add(user["id"])
    await db.comm_messages.update_one(
        {"id": root_id},
        {"$set": {
            "thread_reply_count": new_reply_count,
            "thread_last_reply_at": _now(),
            "thread_last_reply_by": user.get("name", ""),
            "thread_participants": list(participants),
            "updated_at": _now(),
        }}
    )

    reply_out = _ser(reply)

    # Broadcast: real-time update to channel members or DM participants
    if root.get("channel_id"):
        ch = await db.comm_channels.find_one({"id": root["channel_id"]})
        members = ch.get("members", []) if ch else []
        await comm_manager.broadcast_to_users(members, {
            "type": "thread_reply",
            "data": {
                "reply": reply_out,
                "root_id": root_id,
                "channel_id": root["channel_id"],
                "reply_count": new_reply_count,
                "scope": "channel",
            }
        })
    elif root.get("conversation_id"):
        conv = await db.comm_conversations.find_one({"id": root["conversation_id"]})
        if conv:
            for p in conv.get("participants", []):
                await comm_manager.send_to_user(p, {
                    "type": "thread_reply",
                    "data": {
                        "reply": reply_out,
                        "root_id": root_id,
                        "conv_id": root["conversation_id"],
                        "reply_count": new_reply_count,
                        "scope": "dm",
                    }
                })

    # @mentions inside thread reply
    import re as _re
    mentions = _re.findall(r'@([\w\s\-\.]+?)(?=\s|$|@)', content + ' ')
    if mentions and root.get("channel_id"):
        try:
            from routes.notifications import create_notification
            ch_name = (await db.comm_channels.find_one({"id": root["channel_id"]}) or {}).get("name", "")
            for mention_name in mentions:
                mn = mention_name.strip()
                if not mn:
                    continue
                mu = await db.users.find_one({"name": {"$regex": f"^{_re.escape(mn)}$", "$options": "i"}})
                if mu and mu["id"] != user["id"]:
                    await create_notification(
                        db,
                        user_id=mu["id"],
                        notif_type="mention",
                        title=f'Anda disebut oleh {user.get("name", "Seseorang")} di thread #{ch_name}',
                        content=content[:120] + ('...' if len(content) > 120 else ''),
                        source_type="thread",
                        source_id=root_id,
                        source_url=f"#/comm/thread/{root_id}",
                        metadata={"channel_name": ch_name, "message_id": reply["id"], "thread_root_id": root_id},
                    )
        except Exception:
            pass

    # Notify the original root sender (if different from replier and not already in thread)
    if root["sender_id"] != user["id"]:
        try:
            from routes.notifications import create_notification
            ch_name = ""
            if root.get("channel_id"):
                ch = await db.comm_channels.find_one({"id": root["channel_id"]})
                ch_name = ch.get("name", "") if ch else ""
            await create_notification(
                db,
                user_id=root["sender_id"],
                notif_type="thread_reply",
                title=f'{user.get("name", "Seseorang")} membalas thread Anda{(" di #" + ch_name) if ch_name else ""}',
                content=content[:120] + ('...' if len(content) > 120 else ''),
                source_type="thread",
                source_id=root_id,
                source_url=f"#/comm/thread/{root_id}",
                metadata={"channel_name": ch_name, "message_id": reply["id"], "thread_root_id": root_id},
            )
        except Exception:
            pass

    return reply_out


# ─── Endpoints: Read Receipts & Unread ────────────────────────────────────

@router.get("/unread")
async def get_unread_counts(request: Request):
    """Get unread message counts per channel and per DM conversation."""
    user = await require_auth(request)
    db = get_db()
    uid = user["id"]
    receipts = await db.comm_read_receipts.find({"user_id": uid}, {"_id": 0}).to_list(500)
    read_map = {r["ref_id"]: r.get("last_read_at") for r in receipts}

    # Channels
    channels = await db.comm_channels.find(
        {"$or": [{"members": uid}, {"type": "public"}]}, {"id": 1, "_id": 0}
    ).to_list(200)
    channel_counts = {}
    for ch in channels:
        q = {"channel_id": ch["id"]}
        lr = read_map.get(ch["id"])
        if lr:
            q["created_at"] = {"$gt": lr}
        channel_counts[ch["id"]] = await db.comm_messages.count_documents(q)

    # DMs
    convs = await db.comm_conversations.find({"participants": uid}, {"id": 1, "_id": 0}).to_list(200)
    dm_counts = {}
    for conv in convs:
        q = {"conversation_id": conv["id"]}
        lr = read_map.get(conv["id"])
        if lr:
            q["created_at"] = {"$gt": lr}
        dm_counts[conv["id"]] = await db.comm_messages.count_documents(q)

    return {"channels": channel_counts, "dms": dm_counts}


@router.post("/read/{ref_id}")
async def mark_as_read(ref_id: str, request: Request):
    """Mark all messages in a channel or DM conversation as read."""
    user = await require_auth(request)
    db = get_db()
    await db.comm_read_receipts.update_one(
        {"user_id": user["id"], "ref_id": ref_id},
        {"$set": {"user_id": user["id"], "ref_id": ref_id, "last_read_at": _now()}},
        upsert=True
    )
    return {"ok": True}


# ─── Endpoints: Reactions ─────────────────────────────────────────────────

@router.post("/messages/{msg_id}/reaction")
async def toggle_reaction(msg_id: str, request: Request):
    user = await require_auth(request)
    db = get_db()
    body = await request.json()
    emoji = body.get("emoji", "")
    if not emoji:
        raise HTTPException(400, "Emoji wajib diisi.")
    msg = await db.comm_messages.find_one({"id": msg_id})
    if not msg:
        raise HTTPException(404, "Pesan tidak ditemukan.")
    reactions = msg.get("reactions", {}) or {}
    users_for_emoji = reactions.get(emoji, [])
    if user["id"] in users_for_emoji:
        users_for_emoji.remove(user["id"])
    else:
        users_for_emoji.append(user["id"])
    if not users_for_emoji:
        reactions.pop(emoji, None)
    else:
        reactions[emoji] = users_for_emoji
    await db.comm_messages.update_one(
        {"id": msg_id}, {"$set": {"reactions": reactions, "updated_at": _now()}}
    )
    # Broadcast reaction update
    msg_updated = await db.comm_messages.find_one({"id": msg_id}, {"_id": 0})
    broadcast_data = {"type": "reaction_update", "data": {"msg_id": msg_id, "reactions": reactions}}
    if msg.get("channel_id"):
        ch = await db.comm_channels.find_one({"id": msg["channel_id"]}, {"members": 1})
        if ch:
            await comm_manager.broadcast_to_users(ch.get("members", []), broadcast_data)
    elif msg.get("conversation_id"):
        conv = await db.comm_conversations.find_one({"id": msg["conversation_id"]}, {"participants": 1})
        if conv:
            await comm_manager.broadcast_to_users(conv.get("participants", []), broadcast_data)
    return {"ok": True, "reactions": reactions}


# ─── Endpoints: Edit / Delete Message ──────────────────────────────────────────

async def _broadcast_msg_event(db, msg: dict, event_type: str, payload_extra: dict):
    """Broadcast event ke seluruh member channel/peserta DM."""
    data = {"type": event_type, "data": {"msg_id": msg["id"], **payload_extra}}
    if msg.get("channel_id"):
        ch = await db.comm_channels.find_one({"id": msg["channel_id"]}, {"members": 1})
        if ch:
            await comm_manager.broadcast_to_users(ch.get("members", []), data)
    elif msg.get("conversation_id"):
        conv = await db.comm_conversations.find_one({"id": msg["conversation_id"]}, {"participants": 1})
        if conv:
            await comm_manager.broadcast_to_users(conv.get("participants", []), data)


@router.patch("/messages/{msg_id}")
async def edit_message(msg_id: str, request: Request):
    """Edit isi pesan (text). Hanya pemilik pesan yang boleh edit. Tanpa batas waktu."""
    user = await require_auth(request)
    db = get_db()
    msg = await db.comm_messages.find_one({"id": msg_id})
    if not msg:
        raise HTTPException(404, "Pesan tidak ditemukan.")
    if msg.get("sender_id") != user["id"]:
        raise HTTPException(403, "Hanya pemilik pesan yang dapat mengedit.")
    if msg.get("message_type") not in (None, "text"):
        raise HTTPException(400, "Tipe pesan ini tidak bisa diedit.")
    body = await request.json()
    new_content = (body.get("content") or "").strip()
    if not new_content:
        raise HTTPException(400, "Konten tidak boleh kosong.")
    now = _now()
    await db.comm_messages.update_one(
        {"id": msg_id},
        {"$set": {
            "content": new_content,
            "edited": True,
            "edited_at": now,
            "updated_at": now,
        }},
    )
    updated = await db.comm_messages.find_one({"id": msg_id}, {"_id": 0})
    msg_out = _ser(updated)
    # Broadcast ke ruangan terkait
    await _broadcast_msg_event(db, msg, "message_edited", {"message": msg_out})
    return msg_out


@router.delete("/messages/{msg_id}")
async def delete_message(msg_id: str, request: Request):
    """Hard delete pesan. Hanya pemilik pesan (atau admin/superadmin) yang boleh."""
    user = await require_auth(request)
    db = get_db()
    msg = await db.comm_messages.find_one({"id": msg_id})
    if not msg:
        raise HTTPException(404, "Pesan tidak ditemukan.")
    is_owner = msg.get("sender_id") == user["id"]
    is_admin = (user.get("role") in ("admin", "superadmin")) or user.get("is_admin")
    if not (is_owner or is_admin):
        raise HTTPException(403, "Tidak diizinkan menghapus pesan ini.")
    await db.comm_messages.delete_one({"id": msg_id})
    # Update last_message pada channel/conversation jika perlu
    if msg.get("channel_id"):
        last = await db.comm_messages.find_one(
            {"channel_id": msg["channel_id"]}, {"_id": 0}, sort=[("created_at", -1)]
        )
        await db.comm_channels.update_one(
            {"id": msg["channel_id"]},
            {"$set": {
                "last_message": (last or {}).get("content") or (last or {}).get("file_name"),
                "last_message_at": (last or {}).get("created_at"),
                "updated_at": _now(),
            }},
        )
    elif msg.get("conversation_id"):
        last = await db.comm_messages.find_one(
            {"conversation_id": msg["conversation_id"]}, {"_id": 0}, sort=[("created_at", -1)]
        )
        await db.comm_conversations.update_one(
            {"id": msg["conversation_id"]},
            {"$set": {
                "last_message": (last or {}).get("content") or (last or {}).get("file_name"),
                "last_message_at": (last or {}).get("created_at"),
                "updated_at": _now(),
            }},
        )
    # Broadcast event
    await _broadcast_msg_event(db, msg, "message_deleted", {})
    return {"ok": True, "id": msg_id, "deleted": True}


# ─── Endpoints: Pin / Unpin Message ───────────────────────────────────────────

@router.post("/messages/{msg_id}/pin")
async def pin_message(msg_id: str, request: Request):
    """Pin pesan di channel. Hanya admin/superadmin/creator channel yang boleh."""
    user = await require_auth(request)
    db = get_db()
    msg = await db.comm_messages.find_one({"id": msg_id})
    if not msg:
        raise HTTPException(404, "Pesan tidak ditemukan.")
    if not msg.get("channel_id"):
        raise HTTPException(400, "Hanya pesan channel yang bisa di-pin.")
    # Check channel membership
    ch = await db.comm_channels.find_one({"id": msg["channel_id"]}, {"members": 1, "created_by": 1})
    if not ch:
        raise HTTPException(404, "Channel tidak ditemukan.")
    is_admin = user.get("role") in ("admin", "superadmin") or user.get("is_admin")
    in_channel = user["id"] in ch.get("members", [])
    if not (is_admin or in_channel):
        raise HTTPException(403, "Tidak diizinkan pin pesan ini.")
    now = _now()
    await db.comm_messages.update_one(
        {"id": msg_id},
        {"$set": {"pinned": True, "pinned_by": user["id"], "pinned_by_name": user.get("name",""), "pinned_at": now}}
    )
    await db.comm_channels.update_one(
        {"id": msg["channel_id"]},
        {"$addToSet": {"pinned_message_ids": msg_id}}
    )
    await _broadcast_msg_event(db, msg, "message_pinned", {
        "pinned": True, "pinned_by_name": user.get("name",""), "msg_id": msg_id
    })
    return {"ok": True}


@router.delete("/messages/{msg_id}/pin")
async def unpin_message(msg_id: str, request: Request):
    """Unpin pesan dari channel."""
    user = await require_auth(request)
    db = get_db()
    msg = await db.comm_messages.find_one({"id": msg_id})
    if not msg:
        raise HTTPException(404, "Pesan tidak ditemukan.")
    if not msg.get("channel_id"):
        raise HTTPException(400, "Hanya pesan channel yang bisa di-unpin.")
    is_admin = user.get("role") in ("admin", "superadmin") or user.get("is_admin")
    is_pinner = msg.get("pinned_by") == user["id"]
    if not (is_admin or is_pinner):
        raise HTTPException(403, "Tidak diizinkan unpin pesan ini.")
    await db.comm_messages.update_one(
        {"id": msg_id},
        {"$unset": {"pinned": "", "pinned_by": "", "pinned_by_name": "", "pinned_at": ""}}
    )
    await db.comm_channels.update_one(
        {"id": msg["channel_id"]},
        {"$pull": {"pinned_message_ids": msg_id}}
    )
    await _broadcast_msg_event(db, msg, "message_unpinned", {"pinned": False, "msg_id": msg_id})
    return {"ok": True}


@router.get("/channels/{ch_id}/pinned")
async def get_pinned_messages(ch_id: str, request: Request):
    """Ambil semua pesan yang di-pin di channel."""
    user = await require_auth(request)
    db = get_db()
    ch = await db.comm_channels.find_one({"id": ch_id}, {"pinned_message_ids": 1})
    if not ch:
        raise HTTPException(404, "Channel tidak ditemukan.")
    pinned_ids = ch.get("pinned_message_ids", [])
    if not pinned_ids:
        return []
    msgs = await db.comm_messages.find(
        {"id": {"$in": pinned_ids}, "pinned": True},
        {"_id": 0}
    ).to_list(None)
    return [_ser(m) for m in msgs]


# ─── Endpoints: Search ─────────────────────────────────────────────────────────

@router.get("/search")
async def search_messages(
    request: Request,
    q: str = Query(""),
    channel_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
):
    """Cari pesan di semua channel atau channel spesifik."""
    user = await require_auth(request)
    db = get_db()
    if not q.strip():
        return []
    query = {
        "content": {"$regex": q.strip(), "$options": "i"},
        "deleted": {"$ne": True},
    }
    if channel_id:
        query["channel_id"] = channel_id
    msgs = await db.comm_messages.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return [_ser(m) for m in msgs]


# ─── Endpoints: File Upload ────────────────────────────────────────────────

@router.post("/channels/{channel_id}/upload")
async def upload_file_message(channel_id: str, request: Request, file: UploadFile = File(...)):
    user = await require_auth(request)
    db = get_db()
    ch = await db.comm_channels.find_one({"id": channel_id})
    if not ch:
        raise HTTPException(404, "Channel tidak ditemukan.")
    if file.size and file.size > 10 * 1024 * 1024:  # 10MB max
        raise HTTPException(400, "Ukuran file maksimal 10 MB.")
    content_bytes = await file.read()
    storage_path = generate_storage_path(f"comm/{channel_id}", file.filename)
    stored = put_object(storage_path, content_bytes, file.content_type or "application/octet-stream")
    file_url = stored["url"]  # Extract URL string from storage result dict
    return {
        "file_url": file_url,
        "file_name": file.filename,
        "file_size": len(content_bytes),
        "content_type": file.content_type,
    }


# ─── Endpoints: Online Users ──────────────────────────────────────────────

@router.get("/online-users")
async def get_online_users(request: Request):
    user = await require_auth(request)
    return {"online_user_ids": comm_manager.get_online_user_ids()}


# ─── WebSocket Endpoint ───────────────────────────────────────────────────

@router.websocket("/ws")
async def comm_websocket(ws: WebSocket, token: str = ""):
    """
    WebSocket endpoint untuk Communication Hub.
    Client → Server: {"type": "ping"} atau apapun (keep-alive)
    Server → Client:
      {type: "new_message", data: {message, channel_id|conv_id, scope}}
      {type: "reaction_update", data: {msg_id, reactions}}
      {type: "presence", data: {user_id, name, online}}
      {type: "channel_added", data: {channel_id, channel_name}}
      {type: "ping"}
    """
    if not token:
        await ws.close(code=4001, reason="Token required")
        return
    user = verify_token_str(token)
    if not user:
        await ws.close(code=4001, reason="Invalid token")
        return

    user_id = user["id"]
    user_name = user.get("name", "")

    await comm_manager.connect(ws, user_id, user_name)
    # Broadcast presence to others
    await comm_manager.broadcast_presence(user_id, user_name, True)

    try:
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                # Handle any client-sent messages (keep-alive, typing indicators, etc.)
                try:
                    payload = json.loads(data)
                    if payload.get("type") == "typing":
                        # Broadcast typing indicator
                        channel_id = payload.get("channel_id")
                        if channel_id:
                            db = get_db()
                            ch = await db.comm_channels.find_one({"id": channel_id}, {"members": 1})
                            if ch:
                                others = [m for m in ch.get("members", []) if m != user_id]
                                await comm_manager.broadcast_to_users(others, {
                                    "type": "typing",
                                    "data": {"user_id": user_id, "user_name": user_name, "channel_id": channel_id}
                                })
                except Exception:
                    pass
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"[CommWS] Error for {user_name}: {e}")
    finally:
        comm_manager.disconnect(ws, user_id)
        await comm_manager.broadcast_presence(user_id, user_name, False)


# ─── Init indexes ─────────────────────────────────────────────────────────

async def create_comm_indexes(db):
    await db.comm_channels.create_index(["members", "archived"])
    await db.comm_channels.create_index(["type", "archived"])
    await db.comm_messages.create_index([("channel_id", 1), ("created_at", -1)])
    await db.comm_messages.create_index([("conversation_id", 1), ("created_at", -1)])
    await db.comm_conversations.create_index(["participants"])
    await db.comm_read_receipts.create_index([("user_id", 1), ("ref_id", 1)], unique=True)
