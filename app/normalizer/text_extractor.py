"""
Text extractor for converting normalized JSON blocks to plaintext.
"""
from typing import Dict, Any, List, Union


def extract_plain_text(content_json: Dict[str, Any]) -> str:
    """
    Extract plaintext from normalized content JSON.
    
    Args:
        content_json: Content dict with 'sections' or 'blocks' array (and optionally 'metadata')
        
    Returns:
        Plaintext string with newlines as separators
    """
    if not content_json:
        return ""
    
    # First, try to get plain_text from metadata (new format)
    metadata = content_json.get('metadata', {})
    if 'plain_text' in metadata and metadata['plain_text']:
        return metadata['plain_text']
    
    # Try new format: sections
    sections = content_json.get('sections', [])
    if sections:
        return _extract_plain_text_from_sections(sections)
    
    # Fallback to old format: blocks
    blocks = content_json.get('blocks', [])
    if not blocks:
        return ""
    
    text_parts: List[str] = []
    
    for block in blocks:
        block_type = block.get('type')
        
        if block_type == 'header':
            # Add header text
            text = block.get('text', '')
            if text:
                text_parts.append(text)
        
        elif block_type == 'paragraph':
            # Extract text from paragraph
            if 'children' in block:
                # Paragraph with links - extract text from children
                para_text = _extract_text_from_children(block['children'])
                if para_text:
                    text_parts.append(para_text)
            else:
                # Simple paragraph
                text = block.get('text', '')
                if text:
                    text_parts.append(text)
        
        elif block_type == 'list':
            # Extract each list item
            items = block.get('items', [])
            for item in items:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, list):
                    # Item with children (links, etc.)
                    item_text = _extract_text_from_children(item)
                    if item_text:
                        text_parts.append(item_text)
        
        elif block_type == 'code_block':
            # Include code blocks in plaintext
            code = block.get('code', '')
            if code:
                text_parts.append(code)
        
        elif block_type == 'table':
            # Extract text from table rows
            rows = block.get('rows', [])
            for row in rows:
                if isinstance(row, dict):
                    # Row is an object
                    row_text = ' '.join(str(v) for v in row.values() if v)
                    if row_text:
                        text_parts.append(row_text)
                elif isinstance(row, list):
                    # Row is an array
                    row_text = ' '.join(str(cell) for cell in row if cell)
                    if row_text:
                        text_parts.append(row_text)
        
        elif block_type == 'special_block':
            # Extract text from special blocks
            text = block.get('text', '')
            if text:
                text_parts.append(text)
            # Also check for heading in special blocks
            heading = block.get('heading', '')
            if heading:
                text_parts.append(heading)
        
        # Note: We skip 'image' blocks as they don't have meaningful text
        # We skip 'metadata' as it's not part of blocks array
    
    # Join with newlines
    return '\n'.join(text_parts)


def _extract_text_from_children(children: List[Union[str, Dict[str, Any]]]) -> str:
    """
    Extract text from paragraph/list item children (which may contain links).
    
    Args:
        children: List of strings and link objects
        
    Returns:
        Combined text
    """
    text_parts: List[str] = []
    
    for child in children:
        if isinstance(child, str):
            text_parts.append(child)
        elif isinstance(child, dict) and child.get('type') == 'link':
            # Extract link text
            link_text = child.get('text', '')
            if link_text:
                text_parts.append(link_text)
    
    return ''.join(text_parts)


def _extract_plain_text_from_sections(sections: List[Dict[str, Any]]) -> str:
    """
    Extract plaintext from sections format.
    
    Args:
        sections: List of section dicts with 'title', 'type', 'items'
        
    Returns:
        Plaintext string
    """
    text_parts: List[str] = []
    
    for section in sections:
        title = section.get('title', '')
        if title:
            text_parts.append(title)
            text_parts.append('=' * len(title))
        
        section_type = section.get('type', '')
        items = section.get('items', [])
        
        if section_type == 'comparison':
            # Format comparison table as text
            for item in items:
                if isinstance(item, dict):
                    item_parts = []
                    for k, v in item.items():
                        if v:
                            if isinstance(v, list):
                                # Handle list values (e.g., benefits)
                                v_str = ', '.join(str(x) for x in v if x)
                                item_parts.append(f"{k}: {v_str}")
                            else:
                                item_parts.append(f"{k}: {v}")
                    if item_parts:
                        text_parts.append(' | '.join(item_parts))
                elif isinstance(item, list):
                    # Handle list cells
                    cell_strs = []
                    for cell in item:
                        if isinstance(cell, list):
                            cell_strs.append(', '.join(str(x) for x in cell if x))
                        else:
                            cell_strs.append(str(cell))
                    text_parts.append(' | '.join(cell_strs))
        
        elif section_type == 'list':
            for item in items:
                if isinstance(item, str):
                    text_parts.append(f"• {item}")
                elif isinstance(item, dict):
                    item_text = ' | '.join(f"{k}: {v}" for k, v in item.items() if v)
                    text_parts.append(f"• {item_text}")
        
        elif section_type == 'links':
            for item in items:
                if isinstance(item, dict):
                    label = item.get('label', '')
                    url = item.get('url', '')
                    if label:
                        text_parts.append(f"• {label} ({url})")
        
        elif section_type == 'text':
            for item in items:
                if isinstance(item, str) and item.strip():
                    text_parts.append(item)
        
        text_parts.append('')  # Empty line between sections
    
    return '\n'.join(text_parts).strip()

