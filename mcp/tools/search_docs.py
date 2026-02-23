"""
Hybrid search for ELMA365 documentation: keyword + semantic (document + chunks).
"""
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.database.models import Doc, DocChunk
from app.embeddings.embedding_service import EmbeddingService
import logging

logger = logging.getLogger(__name__)


async def search_docs(input_data: Dict[str, Any], db_session: AsyncSession) -> Dict[str, Any]:
    """
    Hybrid search in ELMA365 documentation.
    
    Combines:
    1. Keyword search (fast, using content_plain with pg_trgm)
    2. Semantic search on document-level embeddings
    3. Semantic search on chunk-level embeddings
    
    Args:
        input_data: Dict with 'query' key
        db_session: Database session
    
    Returns:
        Dict with 'keyword_docs', 'semantic_docs', 'semantic_chunks' keys
    """
    query = input_data.get("query", "").strip()
    
    if not query:
        return {
            "keyword_docs": [],
            "semantic_docs": [],
            "semantic_chunks": []
        }
    
    try:
        # 1. Keyword search (fast)
        keyword_docs = await _keyword_search(query, db_session)
        
        # 2. Semantic search (document-level)
        semantic_docs = await _semantic_document_search(query, db_session)
        
        # 3. Semantic search (chunk-level)
        semantic_chunks = await _semantic_chunk_search(query, db_session)
        
        logger.info(
            f"Search for '{query}': "
            f"keyword={len(keyword_docs)}, "
            f"semantic_docs={len(semantic_docs)}, "
            f"semantic_chunks={len(semantic_chunks)}"
        )
        
        return {
            "keyword_docs": keyword_docs,
            "semantic_docs": semantic_docs,
            "semantic_chunks": semantic_chunks
        }
    
    except Exception as e:
        logger.error(f"Error searching docs: {e}", exc_info=True)
        raise


async def _keyword_search(query: str, db_session: AsyncSession) -> List[Dict[str, Any]]:
    """
    Fast keyword search using content_plain with ILIKE and pg_trgm.
    
    Args:
        query: Search query
        db_session: Database session
        
    Returns:
        List of matching documents
    """
    try:
        # Split query into keywords
        keywords = [kw.strip() for kw in query.split() if kw.strip()]
        if not keywords:
            return []
        
        # Build search patterns for ILIKE
        search_patterns = [f"%{kw}%" for kw in keywords]
        
        # Search using ILIKE with OR conditions and pg_trgm similarity for ranking
        from sqlalchemy import or_
        conditions = [
            func.lower(Doc.content_plain).like(func.lower(pattern))
            for pattern in search_patterns
        ]
        
        stmt = select(
            Doc.doc_id,
            Doc.title,
            Doc.section,
            Doc.content_plain
        ).where(
            Doc.content_plain.isnot(None),
            or_(*conditions)
        ).order_by(
            # Order by similarity using pg_trgm
            func.similarity(Doc.content_plain, query).desc()
        ).limit(20)
        
        result = await db_session.execute(stmt)
        rows = result.all()
        
        results = []
        for row in rows:
            snippet = _extract_snippet(row.content_plain or "", query, max_length=200)
            results.append({
                "doc_id": row.doc_id,
                "title": row.title or "",
                "section": row.section or "",
                "snippet": snippet
            })
        
        return results
    
    except Exception as e:
        logger.error(f"Error in keyword search: {e}", exc_info=True)
        return []


async def _semantic_document_search(query: str, db_session: AsyncSession) -> List[Dict[str, Any]]:
    """
    Semantic search using document-level embeddings.
    
    Args:
        query: Search query
        db_session: Database session
        
    Returns:
        List of matching documents
    """
    try:
        # Generate embedding for query
        embedding_service = EmbeddingService()
        query_embedding = await embedding_service.generate_embedding(query)
        
        if not query_embedding:
            logger.warning("Failed to generate embedding for query")
            return []
        
        # Convert embedding list to PostgreSQL array format string
        # pgvector expects array format: '[0.1, 0.2, ...]'
        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
        
        # Search using vector cosine distance
        # Using raw SQL for pgvector operator <-> (cosine distance)
        stmt = text("""
            SELECT doc_id, title, section, content_plain
            FROM docs
            WHERE embedding IS NOT NULL
            ORDER BY embedding <-> CAST(:query_embedding AS vector)
            LIMIT 20
        """)
        
        result = await db_session.execute(
            stmt,
            {"query_embedding": embedding_str}
        )
        rows = result.all()
        
        results = []
        for row in rows:
            snippet = _extract_snippet(row.content_plain or "", query, max_length=200)
            results.append({
                "doc_id": row.doc_id,
                "title": row.title or "",
                "section": row.section or "",
                "snippet": snippet
            })
        
        return results
    
    except Exception as e:
        logger.error(f"Error in semantic document search: {e}", exc_info=True)
        return []


async def _semantic_chunk_search(query: str, db_session: AsyncSession) -> List[Dict[str, Any]]:
    """
    Semantic search using chunk-level embeddings.
    
    Args:
        query: Search query
        db_session: Database session
        
    Returns:
        List of matching chunks with doc_id
    """
    try:
        # Generate embedding for query
        embedding_service = EmbeddingService()
        query_embedding = await embedding_service.generate_embedding(query)
        
        if not query_embedding:
            logger.warning("Failed to generate embedding for query")
            return []
        
        # Convert embedding list to PostgreSQL array format string
        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
        
        # Search using vector cosine distance on chunks
        stmt = text("""
            SELECT 
                dc.chunk_text,
                dc.doc_id,
                d.title,
                d.section
            FROM doc_chunks dc
            JOIN docs d ON dc.doc_id = d.doc_id
            WHERE dc.embedding IS NOT NULL
            ORDER BY dc.embedding <-> CAST(:query_embedding AS vector)
            LIMIT 10
        """)
        
        result = await db_session.execute(
            stmt,
            {"query_embedding": embedding_str}
        )
        rows = result.all()
        
        results = []
        for row in rows:
            snippet = _extract_snippet(row.chunk_text or "", query, max_length=200)
            results.append({
                "doc_id": row.doc_id,
                "title": row.title or "",
                "section": row.section or "",
                "chunk_text": snippet
            })
        
        return results
    
    except Exception as e:
        logger.error(f"Error in semantic chunk search: {e}", exc_info=True)
        return []


def _extract_snippet(text: str, query: str, max_length: int = 200) -> str:
    """Extract a snippet around the query match."""
    if not text:
        return ""
    
    text_lower = text.lower()
    query_lower = query.lower()
    
    # Find first occurrence
    idx = text_lower.find(query_lower)
    
    if idx == -1:
        # No match, return beginning
        return text[:max_length] + "..." if len(text) > max_length else text
    
    # Extract context around match
    start = max(0, idx - 50)
    end = min(len(text), idx + len(query) + 50)
    
    snippet = text[start:end]
    
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    
    return snippet
