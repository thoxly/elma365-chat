"""Knowledge rules API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.services.knowledge_rules_service import KnowledgeRulesService
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-rules", tags=["knowledge-rules"])


class RuleUpdateRequest(BaseModel):
    content: Dict[str, Any]
    updated_by: Optional[str] = None


class RuleResponse(BaseModel):
    rule_type: str
    content: Dict[str, Any]
    version: int
    updated_at: Optional[str]
    updated_by: Optional[str]


@router.get("/", response_model=Dict[str, RuleResponse])
async def get_all_rules(db: AsyncSession = Depends(get_db)):
    """Get all knowledge rules."""
    try:
        service = KnowledgeRulesService(db)
        rules = await service.get_all_rules()
        return {
            rule_type: RuleResponse(
                rule_type=rule_type,
                **rule_data
            )
            for rule_type, rule_data in rules.items()
        }
    except Exception as e:
        logger.error(f"Error getting all rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{rule_type}", response_model=RuleResponse)
async def get_rule(
    rule_type: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a knowledge rule by type."""
    try:
        service = KnowledgeRulesService(db)
        rule = await service.get_rule(rule_type)
        if not rule:
            raise HTTPException(status_code=404, detail=f"Rule '{rule_type}' not found")
        return RuleResponse(**rule)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{rule_type}", response_model=RuleResponse)
async def update_rule(
    rule_type: str,
    request: RuleUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a knowledge rule."""
    try:
        service = KnowledgeRulesService(db)
        rule = await service.update_rule(
            rule_type=rule_type,
            content=request.content,
            updated_by=request.updated_by or "api"
        )
        return RuleResponse(
            rule_type=rule.rule_type,
            content=rule.content,
            version=rule.version,
            updated_at=rule.updated_at.isoformat() if rule.updated_at else None,
            updated_by=rule.updated_by
        )
    except Exception as e:
        logger.error(f"Error updating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))
