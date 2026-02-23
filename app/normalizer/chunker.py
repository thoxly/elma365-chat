"""
Chunker for splitting normalized content into semantic chunks.
"""
from typing import Dict, Any, List, Optional
import tiktoken


class Chunker:
    """Generate semantic chunks from normalized content."""
    
    def __init__(self):
        """Initialize chunker with tiktoken encoder."""
        try:
            self.token_encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.token_encoder = None
    
    def generate_chunks(self, content_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate chunks from normalized content.
        
        Rules:
        - New chunk starts on any block.type == "header"
        - Includes following paragraphs and lists until next header or 1500 chars
        - Structure: {"chunk_index": int, "chunk_text": str, "token_count": int}
        
        Args:
            content_json: Content dict with 'blocks' array
            
        Returns:
            List of chunk dictionaries
        """
        if not content_json:
            return []
        
        blocks = content_json.get('blocks', [])
        if not blocks:
            return []
        
        chunks: List[Dict[str, Any]] = []
        current_chunk_text: List[str] = []
        current_chunk_index = 0
        max_chunk_length = 1500  # characters
        
        i = 0
        while i < len(blocks):
            block = blocks[i]
            block_type = block.get('type')
            
            # New chunk starts on any header
            if block_type == 'header':
                # Save previous chunk if it has content
                if current_chunk_text:
                    chunk_text = '\n'.join(current_chunk_text)
                    token_count = self._count_tokens(chunk_text)
                    chunks.append({
                        'chunk_index': current_chunk_index,
                        'chunk_text': chunk_text,
                        'token_count': token_count
                    })
                    current_chunk_index += 1
                    current_chunk_text = []
                
                # Start new chunk with header
                header_text = block.get('text', '')
                if header_text:
                    current_chunk_text.append(header_text)
            
            # Add paragraphs and lists to current chunk
            elif block_type in ['paragraph', 'list']:
                block_text = self._extract_block_text(block)
                if block_text:
                    # Check if adding this block would exceed max length
                    test_text = '\n'.join(current_chunk_text + [block_text])
                    if len(test_text) > max_chunk_length and current_chunk_text:
                        # Save current chunk and start new one
                        chunk_text = '\n'.join(current_chunk_text)
                        token_count = self._count_tokens(chunk_text)
                        chunks.append({
                            'chunk_index': current_chunk_index,
                            'chunk_text': chunk_text,
                            'token_count': token_count
                        })
                        current_chunk_index += 1
                        current_chunk_text = []
                    
                    current_chunk_text.append(block_text)
            
            # Skip other block types (code_block, table, image, special_block)
            # as they are less suitable for semantic chunking
            
            i += 1
        
        # Save last chunk if it has content
        if current_chunk_text:
            chunk_text = '\n'.join(current_chunk_text)
            token_count = self._count_tokens(chunk_text)
            chunks.append({
                'chunk_index': current_chunk_index,
                'chunk_text': chunk_text,
                'token_count': token_count
            })
        
        return chunks
    
    def _extract_block_text(self, block: Dict[str, Any]) -> str:
        """Extract text from a block."""
        block_type = block.get('type')
        
        if block_type == 'paragraph':
            if 'children' in block:
                # Paragraph with links
                return self._extract_text_from_children(block['children'])
            else:
                return block.get('text', '')
        
        elif block_type == 'list':
            items = block.get('items', [])
            text_parts = []
            for item in items:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, list):
                    item_text = self._extract_text_from_children(item)
                    if item_text:
                        text_parts.append(item_text)
            return '\n'.join(text_parts)
        
        return ''
    
    def _extract_text_from_children(self, children: List[Any]) -> str:
        """Extract text from paragraph/list item children."""
        text_parts = []
        for child in children:
            if isinstance(child, str):
                text_parts.append(child)
            elif isinstance(child, dict) and child.get('type') == 'link':
                link_text = child.get('text', '')
                if link_text:
                    text_parts.append(link_text)
        return ''.join(text_parts)
    
    def _count_tokens(self, text: str) -> Optional[int]:
        """Count tokens in text using tiktoken."""
        if not self.token_encoder or not text:
            return None
        try:
            tokens = self.token_encoder.encode(text)
            return len(tokens)
        except Exception:
            return None

