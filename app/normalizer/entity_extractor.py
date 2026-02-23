from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database.models import Entity


class EntityExtractor:
    """Extract entities from normalized content and save to database."""
    
    def __init__(self):
        pass
    
    async def extract_and_save_entities(
        self,
        session: AsyncSession,
        doc_id: str,
        normalized_content: Dict
    ) -> List[Entity]:
        """
        Extract entities from normalized content and save to database.
        
        Args:
            session: Database session
            doc_id: Document ID
            normalized_content: Normalized content dict with 'blocks' key
        
        Returns:
            List of created Entity objects
        """
        blocks = normalized_content.get('blocks', [])
        
        # Clear existing entities for this document
        await session.execute(
            delete(Entity).where(Entity.doc_id == doc_id)
        )
        
        entities = []
        
        for block in blocks:
            entity = self._block_to_entity(doc_id, block)
            if entity:
                entities.append(entity)
        
        # Bulk insert entities
        if entities:
            session.add_all(entities)
            await session.commit()
        
        return entities
    
    def _block_to_entity(self, doc_id: str, block: Dict) -> Optional[Entity]:
        """Convert a block to an Entity object."""
        block_type = block.get('type')
        
        if block_type == 'header':
            data = {
                'level': block.get('level'),
                'text': block.get('text'),
                'anchor': block.get('id', '')
            }
            # Include kind if present (e.g., 'tab' for tabs)
            if block.get('kind'):
                data['kind'] = block.get('kind')
            return Entity(
                doc_id=doc_id,
                type='header',
                data=data
            )
        
        elif block_type == 'code_block':
            return Entity(
                doc_id=doc_id,
                type='code_block',
                data={
                    'language': block.get('language'),
                    'code': block.get('code'),
                    'context': self._get_context(block)
                }
            )
        
        elif block_type == 'special_block':
            return Entity(
                doc_id=doc_id,
                type='special_block',
                data={
                    'kind': block.get('kind'),
                    'heading': block.get('heading'),
                    'content': block.get('content', [])
                }
            )
        
        elif block_type == 'list':
            return Entity(
                doc_id=doc_id,
                type='list',
                data={
                    'ordered': block.get('ordered', False),
                    'items': block.get('items', []),
                    'context': self._get_context(block)
                }
            )
        
        elif block_type == 'paragraph':
            # Optionally extract paragraphs as entities
            # For now, we'll skip them to avoid too many entities
            # Uncomment if needed:
            # return Entity(
            #     doc_id=doc_id,
            #     type='paragraph',
            #     data={'text': block.get('text')}
            # )
            return None
        
        elif block_type == 'image':
            return Entity(
                doc_id=doc_id,
                type='image',
                data={
                    'src': block.get('src'),
                    'alt': block.get('alt', '')
                }
            )
        
        return None
    
    def _get_context(self, block: Dict) -> str:
        """Extract context for a block (surrounding text)."""
        # This is a placeholder - in a full implementation,
        # we'd look at surrounding blocks
        return ''

