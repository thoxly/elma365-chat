"""Service for managing chat messages and documents."""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database.models import ChatMessage, ChatDocument, TaskTemplate
from app.services.flexible_agent import FlexibleAgent
from app.services.knowledge_rules_service import KnowledgeRulesService
from mcp.client import MCPClient
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """Service for working with chat."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.mcp_client = MCPClient()
        self.rules_service = KnowledgeRulesService(db_session)
    
    async def send_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
        template_id: Optional[int] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send a message in chat and get AI response."""
        # Save user message
        user_msg = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=message,
            template_id=template_id,
            attachments=attachments or []
        )
        self.db_session.add(user_msg)
        await self.db_session.flush()
        
        # Get template if specified
        template = None
        if template_id:
            result = await self.db_session.execute(
                select(TaskTemplate).where(TaskTemplate.id == template_id)
            )
            template = result.scalar_one_or_none()
        
        # Get chat history for context
        history = await self.get_history(user_id, session_id)
        
        # Get documents for this session
        docs_result = await self.db_session.execute(
            select(ChatDocument).where(
                ChatDocument.user_id == user_id,
                ChatDocument.session_id == session_id
            )
        )
        documents = docs_result.scalars().all()
        
        # Prepare context
        context = {
            "history": [
                {"role": msg["role"], "content": msg["content"]}
                for msg in history[-10:]  # Last 10 messages
            ],
            "documents": [
                {"filename": doc.filename, "content": doc.content}
                for doc in documents
            ]
        }
        
        # Execute with flexible agent if template provided, otherwise simple response
        if template:
            agent = FlexibleAgent(template, self.mcp_client, self.rules_service)
            response_content = await agent.execute(message, context)
        else:
            # Simple response without template (can be enhanced later)
            response_content = f"Вы написали: {message}. Для использования шаблонов заданий укажите template_id."
        
        # Save assistant response
        assistant_msg = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=response_content,
            template_id=template_id
        )
        self.db_session.add(assistant_msg)
        await self.db_session.commit()
        await self.db_session.refresh(assistant_msg)
        
        return {
            "message_id": assistant_msg.id,
            "content": response_content,
            "role": "assistant"
        }
    
    async def upload_document(
        self,
        user_id: str,
        session_id: str,
        filename: str,
        content: str,
        file_type: Optional[str] = None
    ) -> ChatDocument:
        """Upload a document to chat context."""
        doc = ChatDocument(
            user_id=user_id,
            session_id=session_id,
            filename=filename,
            content=content,
            file_type=file_type or filename.split('.')[-1] if '.' in filename else 'txt'
        )
        self.db_session.add(doc)
        await self.db_session.commit()
        await self.db_session.refresh(doc)
        return doc
    
    async def get_history(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        result = await self.db_session.execute(
            select(ChatMessage)
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id
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
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in messages
        ]
