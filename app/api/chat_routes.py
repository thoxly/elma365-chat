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


@router.get("/sessions")
async def list_sessions(
    user_id: str,
    db=Depends(get_db_or_supabase),
):
    """List chat sessions for user (for sidebar)."""
    try:
        service = ChatService(db)
        sessions = await service.list_sessions(user_id)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CreateSessionRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None  # если не передан — сгенерировать на бэкенде
    title: Optional[str] = None


@router.post("/sessions")
async def create_session(
    request: CreateSessionRequest,
    db=Depends(get_db_or_supabase),
):
    """Create a new chat session. Returns session_id and title."""
    import uuid
    session_id = request.session_id or f"session-{uuid.uuid4().hex[:12]}"
    try:
        service = ChatService(db)
        await service.ensure_session(request.user_id, session_id, request.title)
        sessions = await service.list_sessions(request.user_id)
        created = next((s for s in sessions if s["session_id"] == session_id), None)
        return {
            "session_id": session_id,
            "title": (created or {}).get("title", request.title or "Новый чат"),
            "created_at": (created or {}).get("created_at"),
        }
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class UpdateSessionRequest(BaseModel):
    title: str


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    user_id: str,
    body: UpdateSessionRequest,
    db=Depends(get_db_or_supabase),
):
    """Update session title."""
    try:
        service = ChatService(db)
        ok = await service.update_session_title(user_id, session_id, body.title)
        if not ok:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"session_id": session_id, "title": body.title}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session: {e}")
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
