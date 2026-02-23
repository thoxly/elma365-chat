from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, String
from app.database.models import Doc, Entity
import logging

logger = logging.getLogger(__name__)

# Pattern keywords mapping
PATTERN_KEYWORDS = {
    "согласование": ["согласование", "согласовать", "approval", "approve", "согласован"],
    "поручение": ["поручение", "поручить", "task", "assignment", "задача"],
    "регистрация": ["регистрация", "зарегистрировать", "registration", "register", "регистр"],
    "архивирование": ["архивирование", "архив", "archive", "archiving", "архивировать"],
    "SLA": ["sla", "service level", "уровень обслуживания", "соглашение об уровне"]
}


def _extract_text_from_blocks(content: Dict[str, Any]) -> str:
    """
    Extract all text from blocks structure.
    
    Args:
        content: Content dict with 'blocks' array
        
    Returns:
        Combined text from all blocks
    """
    if not content:
        return ""
    
    blocks = content.get('blocks', [])
    if not blocks:
        return ""
    
    text_parts = []
    
    for block in blocks:
        block_type = block.get('type')
        
        if block_type == 'header':
            text_parts.append(block.get('text', ''))
        elif block_type == 'paragraph':
            if 'children' in block:
                for child in block['children']:
                    if isinstance(child, str):
                        text_parts.append(child)
                    elif isinstance(child, dict) and child.get('type') == 'link':
                        text_parts.append(child.get('text', ''))
            else:
                text_parts.append(block.get('text', ''))
        elif block_type == 'list':
            items = block.get('items', [])
            for item in items:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, list):
                    for child in item:
                        if isinstance(child, str):
                            text_parts.append(child)
                        elif isinstance(child, dict) and child.get('type') == 'link':
                            text_parts.append(child.get('text', ''))
        elif block_type == 'code_block':
            text_parts.append(block.get('code', ''))
        elif block_type == 'table':
            rows = block.get('rows', [])
            for row in rows:
                if isinstance(row, list):
                    text_parts.extend(str(cell) for cell in row)
                elif isinstance(row, dict):
                    text_parts.extend(str(v) for v in row.values())
        elif block_type == 'special_block':
            text_parts.append(block.get('text', ''))
            text_parts.append(block.get('heading', ''))
    
    return ' '.join(text_parts)


async def find_process_patterns(input_data: Dict[str, Any], db_session: AsyncSession) -> Dict[str, Any]:
    """
    Find process patterns in documentation.
    
    Args:
        input_data: Dict with 'pattern_type' key
        db_session: Database session
    
    Returns:
        Dict with 'patterns' key containing list of process patterns
    """
    pattern_type = input_data.get("pattern_type", "").strip()
    
    if not pattern_type:
        raise ValueError("pattern_type is required")
    
    # Get keywords for this pattern type
    keywords = PATTERN_KEYWORDS.get(pattern_type.lower(), [pattern_type])
    
    if not keywords:
        return {"patterns": []}
    
    try:
        patterns = []
        
        # Search in documents content (blocks structure)
        # Use PostgreSQL JSONB cast to text for searching
        search_patterns = [f"%{kw}%" for kw in keywords]
        
        stmt = select(
            Doc.doc_id,
            Doc.title,
            Doc.section,
            Doc.content
        ).where(
            or_(*[
                func.cast(Doc.content, String).ilike(pattern)
                for pattern in search_patterns
            ])
        ).limit(20)
        
        result = await db_session.execute(stmt)
        docs = result.all()
        
        for doc in docs:
            # Extract text from blocks structure
            content = doc.content or {}
            full_text = _extract_text_from_blocks(content)
            
            # Check if any keyword is in the text
            full_text_lower = full_text.lower()
            if any(kw.lower() in full_text_lower for kw in keywords):
                patterns.append({
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "section": doc.section,
                    "pattern_type": pattern_type,
                    "snippet": _extract_snippet(full_text, keywords[0], max_length=300)
                })
        
        # Also search in entities (special blocks, code blocks)
        entity_stmt = select(Entity).where(
            or_(*[
                Entity.data['kind'].astext.ilike(f"%{kw}%")
                for kw in keywords
            ])
        ).limit(10)
        
        entity_result = await db_session.execute(entity_stmt)
        entities = entity_result.scalars().all()
        
        for entity in entities:
            data = entity.data or {}
            content_text = str(data).lower()
            
            if any(kw.lower() in content_text for kw in keywords):
                patterns.append({
                    "doc_id": entity.doc_id,
                    "type": entity.type,
                    "pattern_type": pattern_type,
                    "data": data
                })
        
        logger.info(f"Found {len(patterns)} patterns of type '{pattern_type}'")
        return {"patterns": patterns}
    
    except Exception as e:
        logger.error(f"Error finding process patterns: {e}", exc_info=True)
        raise


def _extract_snippet(text: str, keyword: str, max_length: int = 300) -> str:
    """Extract a snippet around the keyword match."""
    if not text:
        return ""
    
    text_lower = text.lower()
    keyword_lower = keyword.lower()
    
    idx = text_lower.find(keyword_lower)
    
    if idx == -1:
        return text[:max_length] + "..." if len(text) > max_length else text
    
    start = max(0, idx - 100)
    end = min(len(text), idx + len(keyword) + 100)
    
    snippet = text[start:end]
    
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    
    return snippet

