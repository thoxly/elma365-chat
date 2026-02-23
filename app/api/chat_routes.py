"""Chat API routes."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.services.chat_service import ChatService
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class SendMessageRequest(BaseModel):
    user_id: str
    session_id: str
    message: str
    template_id: Optional[int] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class MessageResponse(BaseModel):
    message_id: int
    content: str
    role: str


@router.post("/messages", response_model=MessageResponse)
async def send_message(
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send a message in chat and get AI response."""
    try:
        service = ChatService(db)
        result = await service.send_message(
            user_id=request.user_id,
            session_id=request.session_id,
            message=request.message,
            template_id=request.template_id,
            attachments=request.attachments
        )
        return MessageResponse(**result)
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents")
async def upload_document(
    user_id: str = Form(...),
    session_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a document to chat context."""
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        
        service = ChatService(db)
        doc = await service.upload_document(
            user_id=user_id,
            session_id=session_id,
            filename=file.filename,
            content=content_str,
            file_type=file.content_type
        )
        return {
            "id": doc.id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
        }
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/history")
async def get_history(
    session_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get chat history for a session."""
    try:
        service = ChatService(db)
        history = await service.get_history(user_id, session_id)
        return {"messages": history}
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
