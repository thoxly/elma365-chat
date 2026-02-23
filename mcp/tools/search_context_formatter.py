"""
Formatter for search results to be presented to LLM.
Converts raw search results into human-readable context format.
"""
from typing import List, Dict, Any


def format_search_context(results: List[Dict[str, Any]]) -> str:
    """
    Format search results as context for LLM.
    
    Format:
    ### Контекст документации ELMA365 (топ-N результатов):
    
    [1] (chunk)
    Источник: doc_id=..., title="...", section="..."
    ---
    <chunk_text>
    
    [2] (document snippet)
    Источник: doc_id=..., title="..."
    ---
    <snippet>
    
    Args:
        results: List of processed search results
    
    Returns:
        Formatted context string
    """
    if not results:
        return ""
    
    lines = [
        f"### Контекст документации ELMA365 (топ-{len(results)} результатов):",
        ""
    ]
    
    for idx, result in enumerate(results, 1):
        doc_id = result.get("doc_id", "unknown")
        title = result.get("title", "")
        section = result.get("section", "")
        source = result.get("_source", "unknown")
        
        # Determine result type
        if "chunk_text" in result:
            result_type = "chunk"
            text = result.get("chunk_text", "")
        else:
            result_type = "document snippet"
            text = result.get("snippet", "")
        
        # Build source line
        source_parts = [f"doc_id={doc_id}"]
        if title:
            source_parts.append(f'title="{title}"')
        if section:
            source_parts.append(f'section="{section}"')
        
        source_line = "Источник: " + ", ".join(source_parts)
        
        # Build formatted entry
        lines.append(f"[{idx}] ({result_type})")
        lines.append(source_line)
        lines.append("---")
        lines.append(text)
        lines.append("")  # Empty line between results
    
    return "\n".join(lines)

