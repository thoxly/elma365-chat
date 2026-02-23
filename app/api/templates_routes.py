"""Task templates API routes (Supabase API or direct DB)."""
from fastapi import APIRouter, Depends, HTTPException
from app.database.supabase_client import get_db_or_supabase
from app.database import supabase_db as sdb
from app.database.models import TaskTemplate
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import ConfigDict
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _is_supabase(db) -> bool:
    return hasattr(db, "table") and callable(getattr(db, "table", None))


def _template_to_response(t) -> Dict[str, Any]:
    """Build TaskTemplateResponse dict from ORM or Supabase row."""
    if isinstance(t, dict):
        return {
            "id": t["id"],
            "name": t["name"],
            "description": t.get("description"),
            "prompt": t["prompt"],
            "system_prompt": t.get("system_prompt"),
            "tools": t.get("tools"),
            "knowledge_rules": t.get("knowledge_rules"),
            "created_at": t.get("created_at"),
            "updated_at": t.get("updated_at"),
            "created_by": t.get("created_by"),
        }
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "prompt": t.prompt,
        "system_prompt": t.system_prompt,
        "tools": t.tools,
        "knowledge_rules": t.knowledge_rules,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
        "created_by": t.created_by,
    }


class TaskTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    prompt: str
    system_prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    knowledge_rules: Optional[List[str]] = None
    created_by: Optional[str] = None


class TaskTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    knowledge_rules: Optional[List[str]] = None


class TaskTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    prompt: str
    system_prompt: Optional[str]
    tools: Optional[List[str]]
    knowledge_rules: Optional[List[str]]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


@router.post("/", response_model=TaskTemplateResponse)
async def create_template(
    template: TaskTemplateCreate,
    db=Depends(get_db_or_supabase),
):
    try:
        if _is_supabase(db):
            row = {
                "name": template.name,
                "description": template.description,
                "prompt": template.prompt,
                "system_prompt": template.system_prompt,
                "tools": template.tools,
                "knowledge_rules": template.knowledge_rules,
                "created_by": template.created_by,
            }
            out = await sdb.template_create(db, row)
            return TaskTemplateResponse(**_template_to_response(out))
        db_template = TaskTemplate(
            name=template.name,
            description=template.description,
            prompt=template.prompt,
            system_prompt=template.system_prompt,
            tools=template.tools,
            knowledge_rules=template.knowledge_rules,
            created_by=template.created_by,
        )
        db.add(db_template)
        await db.commit()
        await db.refresh(db_template)
        return TaskTemplateResponse.model_validate(db_template)
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[TaskTemplateResponse])
async def list_templates(db=Depends(get_db_or_supabase)):
    try:
        if _is_supabase(db):
            templates = await sdb.template_list(db)
            return [TaskTemplateResponse(**_template_to_response(t)) for t in templates]
        result = await db.execute(select(TaskTemplate).order_by(TaskTemplate.created_at.desc()))
        templates = result.scalars().all()
        return [TaskTemplateResponse.model_validate(t) for t in templates]
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}", response_model=TaskTemplateResponse)
async def get_template(
    template_id: int,
    db=Depends(get_db_or_supabase),
):
    try:
        if _is_supabase(db):
            template = await sdb.template_get(db, template_id)
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
            return TaskTemplateResponse(**_template_to_response(template))
        result = await db.execute(select(TaskTemplate).where(TaskTemplate.id == template_id))
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return TaskTemplateResponse.model_validate(template)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{template_id}", response_model=TaskTemplateResponse)
async def update_template(
    template_id: int,
    template: TaskTemplateUpdate,
    db=Depends(get_db_or_supabase),
):
    try:
        if _is_supabase(db):
            t = await sdb.template_get(db, template_id)
            if not t:
                raise HTTPException(status_code=404, detail="Template not found")
            row = {}
            if template.name is not None:
                row["name"] = template.name
            if template.description is not None:
                row["description"] = template.description
            if template.prompt is not None:
                row["prompt"] = template.prompt
            if template.system_prompt is not None:
                row["system_prompt"] = template.system_prompt
            if template.tools is not None:
                row["tools"] = template.tools
            if template.knowledge_rules is not None:
                row["knowledge_rules"] = template.knowledge_rules
            if row:
                out = await sdb.template_update(db, template_id, row)
                return TaskTemplateResponse(**_template_to_response(out))
            return TaskTemplateResponse(**_template_to_response(t))
        result = await db.execute(select(TaskTemplate).where(TaskTemplate.id == template_id))
        db_template = result.scalar_one_or_none()
        if not db_template:
            raise HTTPException(status_code=404, detail="Template not found")
        if template.name is not None:
            db_template.name = template.name
        if template.description is not None:
            db_template.description = template.description
        if template.prompt is not None:
            db_template.prompt = template.prompt
        if template.system_prompt is not None:
            db_template.system_prompt = template.system_prompt
        if template.tools is not None:
            db_template.tools = template.tools
        if template.knowledge_rules is not None:
            db_template.knowledge_rules = template.knowledge_rules
        await db.commit()
        await db.refresh(db_template)
        return TaskTemplateResponse.model_validate(db_template)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db=Depends(get_db_or_supabase),
):
    try:
        if _is_supabase(db):
            t = await sdb.template_get(db, template_id)
            if not t:
                raise HTTPException(status_code=404, detail="Template not found")
            await sdb.template_delete(db, template_id)
            return {"message": "Template deleted successfully"}
        result = await db.execute(select(TaskTemplate).where(TaskTemplate.id == template_id))
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        await db.delete(template)
        await db.commit()
        return {"message": "Template deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))
