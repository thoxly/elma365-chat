from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import Entity
import logging

logger = logging.getLogger(__name__)


async def get_entities(input_data: Dict[str, Any], db_session: AsyncSession) -> Dict[str, Any]:
    """
    Get entities from a document, optionally filtered by type.
    
    Args:
        input_data: Dict with 'doc_id' and optional 'entity_types' keys
        db_session: Database session
    
    Returns:
        Dict with 'entities' key containing list of entities
    """
    doc_id = input_data.get("doc_id", "").strip()
    entity_types = input_data.get("entity_types", [])
    
    if not doc_id:
        raise ValueError("doc_id is required")
    
    try:
        # Build query
        stmt = select(Entity).where(Entity.doc_id == doc_id)
        
        # Filter by types if provided
        if entity_types:
            # Normalize type names (e.g., "code_blocks" -> "code_block")
            normalized_types = []
            for et in entity_types:
                if et.endswith("s"):
                    normalized_types.append(et[:-1])  # Remove plural
                normalized_types.append(et)
            
            stmt = stmt.where(Entity.type.in_(normalized_types))
        
        stmt = stmt.order_by(Entity.created_at)
        
        result = await db_session.execute(stmt)
        entities = result.scalars().all()
        
        # Convert to dict format
        entities_list = []
        for entity in entities:
            entities_list.append({
                "id": entity.id,
                "doc_id": entity.doc_id,
                "type": entity.type,
                "data": entity.data,
                "created_at": entity.created_at.isoformat() if entity.created_at else None
            })
        
        logger.info(f"Retrieved {len(entities_list)} entities for doc_id '{doc_id}'")
        return {"entities": entities_list}
    
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error getting entities for doc_id '{doc_id}': {e}", exc_info=True)
        raise

