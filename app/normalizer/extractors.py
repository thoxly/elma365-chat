from bs4 import BeautifulSoup, Tag, NavigableString
from typing import List, Dict, Optional
import re


class SpecialBlockExtractor:
    """Extract special blocks from ELMA365 documentation."""
    
    # Patterns for special blocks
    SPECIAL_BLOCK_PATTERNS = {
        'В этой статье': [
            r'в этой статье',
            r'in this article',
            r'содержание',
            r'оглавление',
            r'table of contents'
        ],
        'Пример': [
            r'пример',
            r'example',
            r'примеры',
            r'examples'
        ],
        'API': [
            r'api',
            r'endpoint',
            r'endpoints',
            r'метод',
            r'методы'
        ],
        'Важно': [
            r'важно\s*:',
            r'important\s*:',
            r'важно\s*$',
        ],
        'Обратите внимание': [
            r'обратите внимание',
            r'note\s*:',
            r'примечание\s*:',
            r'attention\s*:',
        ],
        'Вкладка': [
            r'вкладка\s*«[^»]+»',
            r'вкладка\s*"[^"]+"',
            r'tab\s*«[^»]+»',
            r'tab\s*"[^"]+"',
        ],
        'Attention': [
            r'начало\s*внимание',
            r'конец\s*внимание',
            r'начало\s*attention',
            r'конец\s*attention',
        ]
    }
    
    def __init__(self):
        pass
    
    def extract_special_blocks(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract all special blocks from HTML."""
        special_blocks = []
        
        for block_type, patterns in self.SPECIAL_BLOCK_PATTERNS.items():
            blocks = self._extract_blocks_by_type(soup, block_type, patterns)
            special_blocks.extend(blocks)
        
        # Extract attention blocks (between markers)
        attention_blocks = self._extract_attention_blocks(soup)
        special_blocks.extend(attention_blocks)
        
        return special_blocks
    
    def _extract_blocks_by_type(self, soup: BeautifulSoup, block_type: str, patterns: List[str]) -> List[Dict]:
        """Extract blocks of a specific type."""
        blocks = []
        
        # Compile regex patterns
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        
        # Search for headings or text that match patterns
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'section', 'span']):
            text = element.get_text(strip=True)
            
            # Check if text matches any pattern
            for pattern in compiled_patterns:
                if pattern.search(text):
                    # Found a potential special block
                    block = self._extract_block_content(element, block_type)
                    if block:
                        blocks.append(block)
                    break
        
        return blocks
    
    def _extract_block_content(self, element: Tag, block_type: str) -> Optional[Dict]:
        """Extract content of a special block starting from the given element."""
        # Get the heading or trigger text
        heading_text = element.get_text(strip=True)
        
        # For "Важно" and "Обратите внимание", the content might be in the same element
        if block_type in ['Важно', 'Обратите внимание']:
            # Check if it's a paragraph with bold span
            if element.name == 'p':
                # Extract full text including content after ":"
                full_text = element.get_text(strip=True)
                # Split by colon to separate label from content
                if ':' in full_text:
                    parts = full_text.split(':', 1)
                    if len(parts) == 2:
                        heading_text = parts[0].strip()
                        content_text = parts[1].strip()
                        if content_text:
                            return {
                                'type': 'special_block',
                                'kind': block_type,
                                'heading': heading_text,
                                'content': [{
                                    'tag': 'p',
                                    'text': content_text,
                                    'html': str(element)
                                }]
                            }
        
        # Find the content that follows this element
        content_elements = []
        current = element.next_sibling
        
        # Collect content until next heading of same or higher level
        if element.name and element.name.startswith('h'):
            heading_level = int(element.name[1])
        else:
            heading_level = 6  # Default to lowest level
        
        while current:
            if isinstance(current, Tag):
                # Stop at next heading of same or higher level
                if current.name and current.name.startswith('h'):
                    next_level = int(current.name[1])
                    if next_level <= heading_level:
                        break
                
                # Collect content
                text = current.get_text(strip=True)
                if text:
                    content_elements.append({
                        'tag': current.name,
                        'text': text,
                        'html': str(current)
                    })
            
            current = current.next_sibling
        
        # Also check parent's siblings if element is a heading
        if not content_elements and element.name and element.name.startswith('h'):
            # Look for next sibling element
            parent = element.parent
            if parent:
                found_element = False
                for sibling in parent.children:
                    if sibling == element:
                        found_element = True
                        continue
                    if found_element and isinstance(sibling, Tag):
                        text = sibling.get_text(strip=True)
                        if text:
                            content_elements.append({
                                'tag': sibling.name,
                                'text': text,
                                'html': str(sibling)
                            })
                            # Stop at next heading
                            if sibling.name and sibling.name.startswith('h'):
                                break
        
        if content_elements or block_type in ['Важно', 'Обратите внимание']:
            return {
                'type': 'special_block',
                'kind': block_type,
                'heading': heading_text,
                'content': content_elements
            }
        
        return None
    
    def _extract_attention_blocks(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract attention blocks between начало внимание / конец внимание markers."""
        blocks = []
        
        # Patterns for different special block types
        block_patterns = {
            'warning': {
                'start': r'начало\s*(внимание|attention)',
                'end': r'конец\s*(внимание|attention)',
                'kind': 'warning'
            },
            'example': {
                'start': r'начало\s*(примера|пример|example)',
                'end': r'конец\s*(примера|пример|example)',
                'kind': 'example'
            },
            'important': {
                'start': r'начало\s*(важно|important)',
                'end': r'конец\s*(важно|important)',
                'kind': 'important'
            }
        }
        
        for block_type, patterns in block_patterns.items():
            start_markers = []
            
            for element in soup.find_all(['p', 'div', 'span', 'code']):
                text = element.get_text(strip=True).lower()
                if re.search(patterns['start'], text, re.I):
                    start_markers.append((element, patterns))
            
            # Extract content between markers
            for start, patterns_info in start_markers:
                current = start.next_sibling
                content_text_parts = []
                
                while current:
                    if isinstance(current, Tag):
                        # Check if this is an end marker
                        text = current.get_text(strip=True).lower()
                        if re.search(patterns_info['end'], text, re.I):
                            break
                        
                        # Collect content (skip the marker itself)
                        text = current.get_text(strip=True)
                        if text and not re.search(patterns_info['start'], text, re.I):
                            content_text_parts.append(text)
                    elif isinstance(current, NavigableString):
                        text = str(current).strip()
                        if text:
                            content_text_parts.append(text)
                    
                    current = current.next_sibling
                
                # Also check parent's siblings
                if not content_text_parts:
                    parent = start.parent
                    if parent:
                        found_start = False
                        for sibling in parent.children:
                            if sibling == start:
                                found_start = True
                                continue
                            if found_start and isinstance(sibling, Tag):
                                text = sibling.get_text(strip=True).lower()
                                if re.search(patterns_info['end'], text, re.I):
                                    break
                                text = sibling.get_text(strip=True)
                                if text and not re.search(patterns_info['start'], text, re.I):
                                    content_text_parts.append(text)
                
                if content_text_parts:
                    # Combine all text
                    combined_text = ' '.join(content_text_parts).strip()
                    if combined_text:
                        blocks.append({
                            'type': 'special_block',
                            'kind': patterns_info['kind'],
                            'text': combined_text
                        })
        
        return blocks
    
    def extract_table_of_contents(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract table of contents (В этой статье)."""
        toc_blocks = self._extract_blocks_by_type(
            soup,
            'В этой статье',
            self.SPECIAL_BLOCK_PATTERNS['В этой статье']
        )
        
        if toc_blocks:
            # Return the first one, or merge them
            return toc_blocks[0]
        
        return None
    
    def extract_examples(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract example blocks (Пример)."""
        return self._extract_blocks_by_type(
            soup,
            'Пример',
            self.SPECIAL_BLOCK_PATTERNS['Пример']
        )
    
    def extract_api_sections(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract API documentation sections."""
        return self._extract_blocks_by_type(
            soup,
            'API',
            self.SPECIAL_BLOCK_PATTERNS['API']
        )
    
    def integrate_special_blocks(self, blocks: List[Dict], special_blocks: List[Dict]) -> List[Dict]:
        """
        Integrate special blocks into the main blocks list.
        Extracts normal blocks from special_block.content and adds them as separate blocks.
        """
        from bs4 import BeautifulSoup
        from app.normalizer.normalizer import Normalizer
        
        result = blocks.copy()
        
        # Process each special block
        for special_block in special_blocks:
            kind = special_block.get('kind', '')
            heading = special_block.get('heading', '')
            content = special_block.get('content', [])
            
            # If special block has heading, add it as a header block
            if heading and len(heading) > 5:  # Only if meaningful heading
                # Try to extract header level from heading text
                header_block = {
                    'type': 'header',
                    'level': 3,  # Default level for special block headers
                    'text': heading,
                    'kind': kind.lower() if kind else None,
                    'semantic_role': 'special_section'
                }
                result.append(header_block)
            
            # Extract normal blocks from special_block.content
            if content:
                normalizer = Normalizer()
                for content_item in content:
                    html = content_item.get('html', '')
                    if html:
                        # Parse HTML and extract blocks
                        soup = BeautifulSoup(html, 'lxml')
                        # Find the main element
                        main_elem = soup.find(['p', 'div', 'ul', 'ol', 'table', 'pre'])
                        if main_elem:
                            parsed = normalizer._parse_element(main_elem)
                            if parsed:
                                if isinstance(parsed, list):
                                    for block in parsed:
                                        # Mark block as part of special section
                                        if isinstance(block, dict):
                                            block['special_section'] = kind
                                            result.append(block)
                                elif isinstance(parsed, dict):
                                    parsed['special_section'] = kind
                                    result.append(parsed)
            
            # Also add a simplified special_block marker (without full content)
            # This preserves the semantic information
            simplified_special = {
                'type': 'special_block',
                'kind': kind,
                'heading': heading[:100] if heading else None,  # Truncate long headings
                'text': heading  # Keep full text for search
            }
            result.append(simplified_special)
        
        return result
