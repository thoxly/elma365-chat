from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import Doc
import logging

logger = logging.getLogger(__name__)


async def get_doc(input_data: Dict[str, Any], db_session: AsyncSession) -> Dict[str, Any]:
    """
    Get a specific document by doc_id.
    
    Args:
        input_data: Dict with 'doc_id' key
        db_session: Database session
    
    Returns:
        Dict with 'doc' key containing document data
    """
    doc_id = input_data.get("doc_id", "").strip()
    
    if not doc_id:
        raise ValueError("doc_id is required")
    
    try:
        stmt = select(Doc).where(Doc.doc_id == doc_id)
        result = await db_session.execute(stmt)
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise ValueError(f"Document with doc_id '{doc_id}' not found")
        
        # Return structured document
        doc_data = {
            "doc_id": doc.doc_id,
            "url": doc.url,
            "title": doc.title,
            "section": doc.section,
            "content": doc.content,  # This contains normalized blocks
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "last_crawled": doc.last_crawled.isoformat() if doc.last_crawled else None
        }
        
        logger.info(f"Retrieved document: {doc_id}")
        return {"doc": doc_data}
    
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error getting doc '{doc_id}': {e}", exc_info=True)
        raise

