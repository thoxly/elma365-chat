"""Chat API routes."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from app.database.supabase_client import get_db_or_supabase
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
    db=Depends(get_db_or_supabase),
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
    db=Depends(get_db_or_supabase),
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
        at = doc.get("uploaded_at") if isinstance(doc, dict) else getattr(doc, "uploaded_at", None)
        uploaded_at = at.isoformat() if hasattr(at, "isoformat") else (at[:24] if at else None)
        return {
            "id": doc.get("id") if isinstance(doc, dict) else getattr(doc, "id", None),
            "filename": doc.get("filename") if isinstance(doc, dict) else getattr(doc, "filename", None),
            "file_type": doc.get("file_type") if isinstance(doc, dict) else getattr(doc, "file_type", None),
            "uploaded_at": uploaded_at,
        }
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/history")
async def get_history(
    session_id: str,
    user_id: str,
    db=Depends(get_db_or_supabase),
):
    """Get chat history for a session."""
    try:
        service = ChatService(db)
        history = await service.get_history(user_id, session_id)
        return {"messages": history}
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
