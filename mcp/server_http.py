from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
from pydantic import BaseModel
import logging

from mcp.core.registry import get_registry, register_all_tools
from mcp.core.executor import ToolExecutor
from app.database import get_db

logger = logging.getLogger(__name__)

# Initialize tools on module import
register_all_tools()

router = APIRouter(prefix="/mcp", tags=["MCP"])

executor = ToolExecutor()


class ToolListResponse(BaseModel):
    tools: List[Dict[str, Any]]


class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ToolCallResponse(BaseModel):
    content: List[Dict[str, Any]]


@router.get("/tools/list", response_model=ToolListResponse)
async def list_tools():
    """List all available MCP tools."""
    registry = get_registry()
    tools = registry.list_tools()
    return {"tools": tools}


@router.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(
    request: ToolCallRequest,
    db: AsyncSession = Depends(get_db)
):
    """Call an MCP tool by name with arguments."""
    try:
        result = await executor.execute_tool(
            name=request.name,
            input_data=request.arguments,
            db_session=db
        )
        return ToolCallResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error calling tool '{request.name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")

