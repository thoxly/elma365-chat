from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.database.models import Entity
import logging

logger = logging.getLogger(__name__)


async def find_examples(input_data: Dict[str, Any], db_session: AsyncSession) -> Dict[str, Any]:
    """
    Find examples in documentation by keywords.
    
    Args:
        input_data: Dict with 'keywords' key (list of strings)
        db_session: Database session
    
    Returns:
        Dict with 'examples' key containing list of examples
    """
    keywords = input_data.get("keywords", [])
    
    if not keywords or not isinstance(keywords, list):
        return {"examples": []}
    
    try:
        # Search for special blocks with kind='Пример'
        stmt = select(Entity).where(
            Entity.type == "special_block"
        )
        
        # Filter by kind='Пример' in data JSONB
        # PostgreSQL JSONB query: data->>'kind' = 'Пример'
        stmt = stmt.where(
            Entity.data['kind'].astext == 'Пример'
        )
        
        result = await db_session.execute(stmt)
        entities = result.scalars().all()
        
        # Filter by keywords in content
        examples = []
        keywords_lower = [k.lower() for k in keywords]
        
        for entity in entities:
            data = entity.data or {}
            content = data.get("content", [])
            
            # Check if any keyword matches in content
            content_text = str(content).lower()
            if any(keyword in content_text for keyword in keywords_lower):
                examples.append({
                    "doc_id": entity.doc_id,
                    "kind": data.get("kind"),
                    "heading": data.get("heading"),
                    "content": content
                })
        
        logger.info(f"Found {len(examples)} examples matching keywords: {keywords}")
        return {"examples": examples}
    
    except Exception as e:
        logger.error(f"Error finding examples: {e}", exc_info=True)
        raise

