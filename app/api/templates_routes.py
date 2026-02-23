"""Task templates API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.database.models import TaskTemplate
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import ConfigDict
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["templates"])


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
    db: AsyncSession = Depends(get_db)
):
    """Create a new task template."""
    try:
        db_template = TaskTemplate(
            name=template.name,
            description=template.description,
            prompt=template.prompt,
            system_prompt=template.system_prompt,
            tools=template.tools,
            knowledge_rules=template.knowledge_rules,
            created_by=template.created_by
        )
        db.add(db_template)
        await db.commit()
        await db.refresh(db_template)
        return TaskTemplateResponse.model_validate(db_template)
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[TaskTemplateResponse])
async def list_templates(db: AsyncSession = Depends(get_db)):
    """List all task templates."""
    try:
        result = await db.execute(select(TaskTemplate).order_by(TaskTemplate.created_at.desc()))
        templates = result.scalars().all()
        return [TaskTemplateResponse.model_validate(t) for t in templates]
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}", response_model=TaskTemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a task template by ID."""
    try:
        result = await db.execute(
            select(TaskTemplate).where(TaskTemplate.id == template_id)
        )
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
    db: AsyncSession = Depends(get_db)
):
    """Update a task template."""
    try:
        result = await db.execute(
            select(TaskTemplate).where(TaskTemplate.id == template_id)
        )
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
    db: AsyncSession = Depends(get_db)
):
    """Delete a task template."""
    try:
        result = await db.execute(
            select(TaskTemplate).where(TaskTemplate.id == template_id)
        )
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
