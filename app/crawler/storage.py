import json
import os
import logging
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.database.models import Doc, DocChunk
from app.utils import normalize_path, extract_outgoing_links
from app.normalizer.text_extractor import extract_plain_text
from app.normalizer.chunker import Chunker
from app.normalizer.normalizer import Normalizer
from app.normalizer.entity_extractor import EntityExtractor
from app.embeddings.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class Storage:
    """Storage handler for crawled documents."""
    
    def __init__(self):
        self.output_dir = Path(settings.OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chunker = Chunker()
        self.embedding_service = EmbeddingService()
        self.normalizer = Normalizer()
        self.entity_extractor = EntityExtractor()
    
    async def save_to_db(self, session: AsyncSession, doc_data: Dict) -> Optional[Doc]:
        """Save or update document in PostgreSQL."""
        try:
            # Normalize HTML content if available
            html = doc_data.get('html', '')
            normalized_content = None
            plain_text_for_db = None
            
            if html:
                # Normalize HTML to structured blocks
                normalized_content = self.normalizer.normalize(
                    html,
                    title=doc_data.get('title'),
                    breadcrumbs=doc_data.get('breadcrumbs', []),
                    source_url=doc_data.get('url')
                )
                logger.info(f"Normalized content for {doc_data.get('doc_id')}: {len(normalized_content.get('blocks', []))} blocks")
                
                # Get clean plain_text from normalized content (not from raw HTML)
                plain_text_for_db = normalized_content.get('metadata', {}).get('plain_text', '')
            
            # Prepare data for JSONB content field - ONLY normalized data, NO raw HTML
            if normalized_content:
                # Save only normalized structured data
                content_data = {
                    'blocks': normalized_content.get('blocks', []),
                    'sections': normalized_content.get('sections', []),
                    'metadata': normalized_content.get('metadata', {})
                }
            else:
                # Fallback: if normalization failed, save minimal data
                content_data = {
                    'blocks': [],
                    'metadata': {
                        'title': doc_data.get('title'),
                        'source_url': doc_data.get('url'),
                        'plain_text': doc_data.get('plain_text', '')
                    }
                }
                plain_text_for_db = doc_data.get('plain_text', '')
            
            # Compute normalized_path for navigation
            normalized_path = normalize_path(doc_data['url'])
            
            # Extract outgoing_links from normalized blocks if available
            outgoing_links = None
            if normalized_content and 'blocks' in normalized_content:
                outgoing_links = extract_outgoing_links(normalized_content['blocks'])
            
            # Use PostgreSQL upsert (INSERT ... ON CONFLICT)
            stmt = insert(Doc).values(
                doc_id=doc_data['doc_id'],
                url=doc_data['url'],
                normalized_path=normalized_path,
                outgoing_links=outgoing_links,
                title=doc_data.get('title'),
                section=doc_data.get('section'),
                content=content_data,
                content_plain=plain_text_for_db,  # Clean plaintext from normalized content
                last_crawled=doc_data.get('last_crawled', datetime.now())
            )
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['doc_id'],
                set_=dict(
                    url=stmt.excluded.url,
                    normalized_path=stmt.excluded.normalized_path,
                    outgoing_links=stmt.excluded.outgoing_links,
                    title=stmt.excluded.title,
                    section=stmt.excluded.section,
                    content=stmt.excluded.content,
                    last_crawled=stmt.excluded.last_crawled
                )
            )
            
            await session.execute(stmt)
            await session.commit()
            
            # Fetch the saved document
            result = await session.execute(
                select(Doc).where(Doc.doc_id == doc_data['doc_id'])
            )
            doc = result.scalar_one_or_none()
            
            # Process embeddings and extract entities if normalized content is available
            if doc and normalized_content:
                # Extract entities (optional - skip if table doesn't exist)
                try:
                    await self.entity_extractor.extract_and_save_entities(
                        session,
                        doc.doc_id,
                        normalized_content
                    )
                    logger.info(f"Extracted entities for {doc.doc_id}")
                except Exception as e:
                    # Log but don't fail - entities table might not exist
                    logger.debug(f"Could not extract entities for {doc.doc_id}: {e}")
                
                # Process embeddings (plaintext, chunks, embeddings)
                await self._process_embeddings(session, doc.doc_id, normalized_content)
            
            logger.info(f"Saved document to DB: {doc_data['doc_id']}")
            return doc
        
        except Exception as e:
            logger.error(f"Error saving document to DB: {e}")
            await session.rollback()
            return None
    
    def save_to_json(self, doc_data: Dict) -> Optional[str]:
        """Save document to local JSON file."""
        try:
            doc_id = doc_data['doc_id']
            # Sanitize filename
            safe_filename = doc_id.replace('/', '_').replace('\\', '_')
            filepath = self.output_dir / f"{safe_filename}.json"
            
            # Prepare JSON data
            json_data = {
                'doc_id': doc_data['doc_id'],
                'url': doc_data['url'],
                'title': doc_data.get('title'),
                'breadcrumbs': doc_data.get('breadcrumbs', []),
                'section': doc_data.get('section'),
                'html': doc_data.get('html'),
                'plain_text': doc_data.get('plain_text'),
                'links': doc_data.get('links', []),
                'last_crawled': doc_data.get('last_crawled').isoformat() if doc_data.get('last_crawled') else None,
                'metadata': {
                    'depth': doc_data.get('depth', 0),
                    'saved_at': datetime.now().isoformat()
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved document to JSON: {filepath}")
            return str(filepath)
        
        except Exception as e:
            logger.error(f"Error saving document to JSON: {e}")
            return None
    
    async def _process_embeddings(
        self, 
        session: AsyncSession, 
        doc_id: str, 
        normalized_content: Dict
    ) -> None:
        """
        Process embeddings for normalized content: extract plaintext, create chunks, generate embeddings.
        
        Args:
            session: Database session
            doc_id: Document ID
            normalized_content: Normalized content dict with 'blocks' array
        """
        try:
            # Extract plaintext
            content_plain = extract_plain_text(normalized_content)
            
            # Generate chunks
            chunks = self.chunker.generate_chunks(normalized_content)
            
            # Generate embeddings
            doc_embedding = None
            if content_plain:
                doc_embedding = await self.embedding_service.generate_embedding(content_plain)
            
            # Generate embeddings for chunks
            chunk_embeddings: List[Optional[List[float]]] = []
            if chunks:
                chunk_texts = [chunk['chunk_text'] for chunk in chunks]
                chunk_embeddings = await self.embedding_service.generate_embeddings_batch(chunk_texts)
            
            # Update document with plaintext and embedding
            if content_plain or doc_embedding:
                update_stmt = select(Doc).where(Doc.doc_id == doc_id)
                result = await session.execute(update_stmt)
                doc = result.scalar_one_or_none()
                
                if doc:
                    if content_plain:
                        doc.content_plain = content_plain
                    if doc_embedding:
                        doc.embedding = doc_embedding
                    await session.commit()
            
            # Delete old chunks
            await session.execute(
                delete(DocChunk).where(DocChunk.doc_id == doc_id)
            )
            
            # Insert new chunks with embeddings
            if chunks:
                chunk_objects = []
                for i, chunk in enumerate(chunks):
                    chunk_obj = DocChunk(
                        doc_id=doc_id,
                        chunk_index=chunk['chunk_index'],
                        chunk_text=chunk['chunk_text'],
                        token_count=chunk.get('token_count'),
                        embedding=chunk_embeddings[i] if i < len(chunk_embeddings) else None
                    )
                    chunk_objects.append(chunk_obj)
                
                session.add_all(chunk_objects)
                await session.commit()
                
                logger.info(f"Processed embeddings for {doc_id}: {len(chunks)} chunks")
        
        except Exception as e:
            logger.error(f"Error processing embeddings for {doc_id}: {e}", exc_info=True)
            await session.rollback()
    
    async def process_embeddings_for_doc(
        self,
        session: AsyncSession,
        doc: Doc
    ) -> None:
        """
        Process embeddings for an existing document.
        
        Args:
            session: Database session
            doc: Doc object with normalized content
        """
        if not doc.content or 'blocks' not in doc.content:
            logger.warning(f"Document {doc.doc_id} has no normalized content")
            return
        
        await self._process_embeddings(session, doc.doc_id, doc.content)
    
    async def save(self, session: AsyncSession, doc_data: Dict) -> Dict:
        """Save document to both database and local JSON file."""
        db_doc = await self.save_to_db(session, doc_data)
        json_path = self.save_to_json(doc_data)
        
        return {
            'doc_id': doc_data['doc_id'],
            'db_saved': db_doc is not None,
            'json_saved': json_path is not None,
            'json_path': json_path
        }

