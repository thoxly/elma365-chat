"""Service for managing chat messages and documents (Supabase API or direct DB)."""
from types import SimpleNamespace
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import ChatMessage, ChatDocument, TaskTemplate
from app.database import supabase_db as sdb
from app.services.flexible_agent import FlexibleAgent
from app.services.knowledge_rules_service import KnowledgeRulesService
from mcp.client import MCPClient
import logging

logger = logging.getLogger(__name__)


def _is_supabase(db: Any) -> bool:
    return hasattr(db, "table") and callable(getattr(db, "table", None))


class ChatService:
    """Service for working with chat (Supabase client or SQLAlchemy session)."""

    def __init__(self, db: Union[AsyncSession, Any]):
        self._db = db
        self._supabase = db if _is_supabase(db) else None
        self.mcp_client = MCPClient()
        self.rules_service = KnowledgeRulesService(db)

    async def send_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
        template_id: Optional[int] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send a message in chat and get AI response."""
        if self._supabase:
            return await self._send_message_supabase(
                user_id, session_id, message, template_id, attachments
            )
        return await self._send_message_sql(user_id, session_id, message, template_id, attachments)

    async def _send_message_supabase(
        self,
        user_id: str,
        session_id: str,
        message: str,
        template_id: Optional[int] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        sb = self._supabase
        user_row = {
            "user_id": user_id,
            "session_id": session_id,
            "role": "user",
            "content": message,
            "template_id": template_id,
            "attachments": attachments or [],
        }
        await sdb.message_insert(sb, user_row)

        template = None
        if template_id:
            template = await sdb.template_get(sb, template_id)

        history = await self.get_history(user_id, session_id)
        documents = await sdb.documents_list(sb, user_id, session_id)
        context = {
            "history": [{"role": m["role"], "content": m["content"]} for m in history[-10:]],
            "documents": [{"filename": d["filename"], "content": d["content"]} for d in documents],
        }

        if template:
            t = SimpleNamespace(**template) if isinstance(template, dict) else template
            agent = FlexibleAgent(t, self.mcp_client, self.rules_service)
            response_content = await agent.execute(message, context)
        else:
            response_content = f"Вы написали: {message}. Для использования шаблонов заданий укажите template_id."

        assistant_row = {
            "user_id": user_id,
            "session_id": session_id,
            "role": "assistant",
            "content": response_content,
            "template_id": template_id,
        }
        assistant_msg = await sdb.message_insert(sb, assistant_row)
        return {
            "message_id": assistant_msg["id"],
            "content": response_content,
            "role": "assistant",
        }

    async def _send_message_sql(
        self,
        user_id: str,
        session_id: str,
        message: str,
        template_id: Optional[int] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        db = self._db
        user_msg = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=message,
            template_id=template_id,
            attachments=attachments or [],
        )
        db.add(user_msg)
        await db.flush()

        template = None
        if template_id:
            result = await db.execute(select(TaskTemplate).where(TaskTemplate.id == template_id))
            template = result.scalar_one_or_none()

        history = await self.get_history(user_id, session_id)
        docs_result = await db.execute(
            select(ChatDocument).where(
                ChatDocument.user_id == user_id,
                ChatDocument.session_id == session_id,
            )
        )
        documents = docs_result.scalars().all()
        context = {
            "history": [{"role": m["role"], "content": m["content"]} for m in history[-10:]],
            "documents": [{"filename": d.filename, "content": d.content} for d in documents],
        }

        if template:
            agent = FlexibleAgent(template, self.mcp_client, self.rules_service)
            response_content = await agent.execute(message, context)
        else:
            response_content = f"Вы написали: {message}. Для использования шаблонов заданий укажите template_id."

        assistant_msg = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=response_content,
            template_id=template_id,
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)
        return {
            "message_id": assistant_msg.id,
            "content": response_content,
            "role": "assistant",
        }

    async def upload_document(
        self,
        user_id: str,
        session_id: str,
        filename: str,
        content: str,
        file_type: Optional[str] = None,
    ) -> Any:
        """Upload a document to chat context."""
        if self._supabase:
            row = {
                "user_id": user_id,
                "session_id": session_id,
                "filename": filename,
                "content": content,
                "file_type": file_type or (filename.split(".")[-1] if "." in filename else "txt"),
            }
            return await sdb.document_insert(self._supabase, row)
        doc = ChatDocument(
            user_id=user_id,
            session_id=session_id,
            filename=filename,
            content=content,
            file_type=file_type or (filename.split(".")[-1] if "." in filename else "txt"),
        )
        self._db.add(doc)
        await self._db.commit()
        await self._db.refresh(doc)
        return doc

    async def get_history(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        if self._supabase:
            messages = await sdb.messages_list(self._supabase, user_id, session_id)
            return [
                {
                    "id": m["id"],
                    "role": m["role"],
                    "content": m["content"],
                    "template_id": m.get("template_id"),
                    "attachments": m.get("attachments"),
                    "created_at": m["created_at"][:24] if m.get("created_at") else None,
                }
                for m in messages
            ]
        result = await self._db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
            )
            .order_by(ChatMessage.created_at)
        )
        messages = result.scalars().all()
        return [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "template_id": msg.template_id,
                "attachments": msg.attachments,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages
        ]
