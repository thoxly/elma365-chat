"""
Post-processing layer for search results.
Combines, deduplicates, ranks, and limits search results.
"""
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

# Scoring weights for different result types
SCORE_SEMANTIC_CHUNK = 3
SCORE_SEMANTIC_DOC = 2
SCORE_KEYWORD_DOC = 1

# Limits
MAX_RESULTS = 10
MAX_CHARS = 5000


def process_search_results(
    keyword_docs: List[Dict[str, Any]],
    semantic_docs: List[Dict[str, Any]],
    semantic_chunks: List[Dict[str, Any]],
    query: str
) -> List[Dict[str, Any]]:
    """
    Process and combine search results from different sources.
    
    Steps:
    1. Combine all results with scores
    2. Deduplicate by doc_id
    3. Sort by score
    4. Limit to top-N results
    5. Limit by character count
    
    Args:
        keyword_docs: Keyword search results
        semantic_docs: Semantic document-level search results
        semantic_chunks: Semantic chunk-level search results
        query: Original search query (for logging)
    
    Returns:
        List of processed results, sorted by relevance
    """
    # Step 1: Combine all results with scores
    combined = []
    
    # Add semantic chunks (highest priority)
    for chunk in semantic_chunks:
        combined.append({
            **chunk,
            "_score": SCORE_SEMANTIC_CHUNK,
            "_source": "semantic_chunk"
        })
    
    # Add semantic docs
    for doc in semantic_docs:
        combined.append({
            **doc,
            "_score": SCORE_SEMANTIC_DOC,
            "_source": "semantic_doc"
        })
    
    # Add keyword docs (lowest priority)
    for doc in keyword_docs:
        combined.append({
            **doc,
            "_score": SCORE_KEYWORD_DOC,
            "_source": "keyword_doc"
        })
    
    # Step 2: Deduplicate by doc_id
    # Keep the result with highest score if duplicate
    seen_doc_ids = {}
    for result in combined:
        doc_id = result.get("doc_id")
        if not doc_id:
            # If no doc_id, keep as is (shouldn't happen, but safe)
            continue
        
        if doc_id not in seen_doc_ids:
            seen_doc_ids[doc_id] = result
        else:
            # If duplicate, keep the one with higher score
            existing_score = seen_doc_ids[doc_id].get("_score", 0)
            new_score = result.get("_score", 0)
            if new_score > existing_score:
                seen_doc_ids[doc_id] = result
    
    # Step 3: Sort by score (descending)
    deduplicated = list(seen_doc_ids.values())
    deduplicated.sort(key=lambda x: x.get("_score", 0), reverse=True)
    
    # Step 4: Limit to top-N results
    top_results = deduplicated[:MAX_RESULTS]
    
    # Step 5: Limit by character count
    final_results = []
    total_chars = 0
    
    for result in top_results:
        # Calculate text length
        text = result.get("chunk_text") or result.get("snippet", "")
        text_length = len(text)
        
        # Check if adding this result would exceed limit
        if total_chars + text_length > MAX_CHARS and final_results:
            # Stop if we already have some results
            break
        
        final_results.append(result)
        total_chars += text_length
    
    # Log processing results
    logger.info(
        f"[Search] query=\"{query}\" | "
        f"input: keyword={len(keyword_docs)}, semantic_docs={len(semantic_docs)}, semantic_chunks={len(semantic_chunks)} | "
        f"after_dedup: {len(deduplicated)} | "
        f"final: {len(final_results)} results, {total_chars} chars"
    )
    
    # Log final result IDs
    if final_results:
        result_ids = [
            f"doc_id={r.get('doc_id', 'unknown')}"
            for r in final_results
        ]
        logger.info(f"[Search] final_results={result_ids}")
    else:
        logger.info(f"[Search] NO_RESULTS")
    
    return final_results

