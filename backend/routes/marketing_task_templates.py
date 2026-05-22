"""
Session 12 — P1-6: Task Auto-Creation dari Template
Manajemen task templates untuk automation via APScheduler.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel, Field
from database import get_db
from auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/marketing/task-templates", tags=["marketing-task-templates"])


def _now():
    return datetime.now(timezone.utc)


def ok(data=None, meta=None):
    r = {"success": True}
    if data is not None:
        r["data"] = data
    if meta is not None:
        r["metadata"] = meta
    return r


def serialize(o):
    if isinstance(o, list):
        return [serialize(i) for i in o]
    if isinstance(o, dict):
        return {k: serialize(v) for k, v in o.items() if k != "_id"}
    if isinstance(o, datetime):
        return o.isoformat()
    return o


# ═══════════════════════════════════════════════════════════════════════════
#  TASK TEMPLATE CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TaskTemplateIn(BaseModel):
    name: str = Field(..., description="Nama template")
    description: Optional[str] = Field(None, description="Deskripsi template")
    task_title: str = Field(..., description="Title task yang akan dibuat")
    task_description: Optional[str] = Field(None, description="Deskripsi task")
    recurrence: str = Field(..., description="daily, weekly, monthly")
    recurrence_day: Optional[int] = Field(None, description="Untuk weekly (1-7) atau monthly (1-31)")
    assigned_to: Optional[str] = Field(None, description="Email user yang ditugaskan")
    priority: Optional[str] = Field("medium", description="low, medium, high")
    tags: Optional[List[str]] = Field(None, description="Tags untuk task")
    active: Optional[bool] = Field(True, description="Template aktif atau tidak")


@router.get("/")
async def list_templates(request: Request):
    """List semua task templates."""
    await require_auth(request)
    db = get_db()
    
    docs = await db.marketing_task_templates.find({}).sort("created_at", -1).to_list(length=100)
    
    return ok(data=serialize(docs), meta={"count": len(docs)})


@router.post("/")
async def create_template(payload: TaskTemplateIn, request: Request):
    """Create task template baru."""
    await require_auth(request)
    db = get_db()
    
    doc = {
        "template_id": str(uuid.uuid4()),
        **payload.dict(),
        "created_at": _now(),
        "updated_at": _now(),
        "last_executed": None,
        "execution_count": 0
    }
    
    await db.marketing_task_templates.insert_one(doc)
    
    logger.info(f"[task-templates] created: {doc['template_id']} - {doc['name']}")
    
    return ok(data=serialize(doc))


@router.put("/{template_id}")
async def update_template(template_id: str, payload: TaskTemplateIn, request: Request):
    """Update task template."""
    await require_auth(request)
    db = get_db()
    
    existing = await db.marketing_task_templates.find_one({"template_id": template_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_data = {**payload.dict(), "updated_at": _now()}
    
    await db.marketing_task_templates.update_one(
        {"template_id": template_id},
        {"$set": update_data}
    )
    
    updated = await db.marketing_task_templates.find_one({"template_id": template_id})
    
    logger.info(f"[task-templates] updated: {template_id}")
    
    return ok(data=serialize(updated))


@router.delete("/{template_id}")
async def delete_template(template_id: str, request: Request):
    """Delete task template."""
    await require_auth(request)
    db = get_db()
    
    result = await db.marketing_task_templates.delete_one({"template_id": template_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    logger.info(f"[task-templates] deleted: {template_id}")
    
    return ok(data={"deleted": True, "template_id": template_id})


# ═══════════════════════════════════════════════════════════════════════════
#  TEMPLATE EXECUTION LOG
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/{template_id}/executions")
async def get_template_executions(template_id: str, request: Request):
    """Get execution log untuk template tertentu."""
    await require_auth(request)
    db = get_db()
    
    template = await db.marketing_task_templates.find_one({"template_id": template_id})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Get tasks yang dibuat dari template ini
    tasks = await db.marketing_tasks.find(
        {"created_from_template": template_id}
    ).sort("created_at", -1).limit(50).to_list(length=50)
    
    return ok(data=serialize(tasks), meta={"count": len(tasks), "template_id": template_id})
