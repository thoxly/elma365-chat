from bs4 import BeautifulSoup, Tag, NavigableString
from typing import List, Dict, Optional, Union, Tuple
import re
from datetime import datetime
from urllib.parse import urlparse, urljoin
from unidecode import unidecode
import tiktoken
from app.normalizer.extractors import SpecialBlockExtractor


class Normalizer:
    """Normalizer for cleaning and structuring HTML content for ELMA365 documentation."""
    
    # ELMA365 specific boilerplate selectors
    BOILERPLATE_SELECTORS = [
        'nav',  # Navigation
        'header',  # Header
        'footer',  # Footer
        '.navbar',  # Navbar class
        '.footer',  # Footer class
        '.header',  # Header class
        '.sidebar',  # Sidebar
        '.menu',  # Menu
        '.navigation',  # Navigation
        'script',  # Scripts
        'style',  # Styles
        '.cookie',  # Cookie notices
        '.modal',  # Modals
        '.popup',  # Popups
        # ELMA365 specific commercial navigation
        '.header__list',
        '.footer-container',
        '.footer-mobile',
        '.bottom-nav',
        '.feedback-wrap',
        '.feedback',
        '.feedback-form',
        '.feedback__popup',
        '.question__popup',
        '.article__sidebar',  # ToC справа
        # Breadcrumbs (navigation structure, not article structure)
        '.article__bread',
        '.topic__breadcrumbs',
        # Note: .article__header is NOT removed - it contains h1 title
        # Social links
        '.social-links-header',
        '.social-footer-img',
        '.footer-url-elma',
        # Next/Prev navigation
        '.topic__navi_prev',
        '.topic__navi_next',
    ]
    
    # Stoplist for semantic noise filtering
    SEMANTIC_NOISE_PATTERNS = [
        r'была ли статья полезной',
        r'спасибо за',
        r'ваш отзыв',
        r'elma365\.com',
        r'academy',
        r'community',
        r'задать вопрос',
        r'©\s*\d{4}\s*elma365',
    ]
    
    # Decorative image patterns (to be filtered out)
    DECORATIVE_IMAGE_PATTERNS = [
        r'approval_\d+\.png',
        r'hmfile_hash_\w+\.png',
        r'^[^/]*\.png$',  # Simple filenames without path
    ]
    
    def __init__(self):
        self.extractor = SpecialBlockExtractor()
        # Initialize tiktoken encoder (cl100k_base is used by GPT models)
        try:
            self.token_encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.token_encoder = None
        # Track header IDs for uniqueness
        self._header_ids = set()
    
    def normalize(
        self, 
        html: str, 
        title: Optional[str] = None, 
        breadcrumbs: Optional[List[str]] = None,
        source_url: Optional[str] = None
    ) -> Dict:
        """
        Normalize HTML content into structured blocks.
        
        Args:
            html: HTML content to normalize
            title: Document title
            breadcrumbs: Breadcrumbs list
            source_url: Source URL of the document
        
        Returns:
            {
                "blocks": [...],
                "metadata": {...}
            }
        """
        # Reset header IDs for each normalization
        self._header_ids = set()
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract h1 BEFORE removing boilerplate (it might be in .article__header)
        h1_title = None
        article_header = soup.select_one('article.article .article__header h1, article.article .topic__title h1')
        if article_header:
            h1_title = article_header.get_text(strip=True)
        else:
            h1 = soup.find('h1')
            if h1:
                h1_title = h1.get_text(strip=True)
        
        # Remove boilerplate
        cleaned_soup = self.remove_boilerplate(soup)
        
        # Normalize HTML structure (flatten dropdowns, normalize text)
        cleaned_soup = self._normalize_html_structure(cleaned_soup)
        
        # Extract special blocks BEFORE parsing (to remove markers)
        special_blocks = self.extractor.extract_special_blocks(cleaned_soup)
        
        # Remove special block markers from soup
        self._remove_special_block_markers(cleaned_soup)
        
        # Parse into structured blocks
        blocks = self.parse_blocks(cleaned_soup)
        
        # Integrate special blocks
        blocks = self.extractor.integrate_special_blocks(blocks, special_blocks)
        
        # Post-filter semantic noise
        blocks = self._filter_semantic_noise(blocks)
        
        # Validate blocks
        blocks = self._validate_blocks(blocks)
        
        # Add semantic roles
        blocks = self._add_semantic_roles(blocks)
        
        # Add token counts
        blocks = self._add_token_counts(blocks)
        
        # Group blocks into semantic sections
        sections = self._group_blocks_into_sections(blocks)
        
        # Remove tables from blocks if they're already in sections (avoid duplication)
        blocks = self._remove_duplicate_tables_from_blocks(blocks, sections)
        
        # Extract plain text (canonical text without HTML) - includes all sections
        plain_text = self._extract_plain_text_from_sections(sections)
        
        # Restore breadcrumbs from URL if not provided
        if not breadcrumbs and source_url:
            breadcrumbs = self._extract_breadcrumbs_from_url(source_url)
        
        # Build metadata (use original soup for h1 extraction, not cleaned)
        # Pass h1_title explicitly to ensure it's included
        metadata = self._build_metadata(soup, blocks, title or h1_title, breadcrumbs, special_blocks, source_url)
        # Add h1 to headers if not already there
        if h1_title and h1_title not in metadata.get('headers', []):
            if 'headers' not in metadata:
                metadata['headers'] = []
            metadata['headers'].insert(0, h1_title)
        
        # Add plain text to metadata
        metadata['plain_text'] = plain_text
        
        return {
            'sections': sections,
            'blocks': blocks,  # Keep for backward compatibility
            'metadata': metadata
        }
    
    def remove_boilerplate(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Remove boilerplate elements from HTML."""
        # Remove by selectors
        for selector in self.BOILERPLATE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()
        
        # Remove <aside> inside <main> (usually left navigation)
        for main in soup.find_all('main'):
            for aside in main.find_all('aside'):
                aside.decompose()
        
        # Remove analytics scripts
        for script in soup.find_all('script'):
            src = script.get('src', '')
            if 'gtag' in src.lower() or 'metrika' in src.lower():
                script.decompose()
        
        # Remove Yandex Metrika noscript
        for noscript in soup.find_all('noscript'):
            for img in noscript.find_all('img'):
                src = img.get('src', '')
                if 'mc.yandex' in src.lower():
                    noscript.decompose()
                    break
        
        # Remove common ELMA365 specific elements
        # Footer text patterns
        for element in soup.find_all(string=re.compile(r'©.*ELMA365', re.I)):
            parent = element.parent
            if parent:
                parent.decompose()
        
        # Flatten dropdowns and popovers (replace with simple div)
        for element in soup.find_all(class_=re.compile(r'feedback|question|dropdown-toggle-body')):
            # Replace with div, keep content
            element.name = 'div'
            for attr in list(element.attrs.keys()):
                if attr != 'class':
                    del element[attr]
            # Remove dropdown-toggle class but keep content
            if 'dropdown-toggle' in element.get('class', []):
                element['class'] = [c for c in element.get('class', []) if 'dropdown-toggle' not in c]
        
        # Remove empty elements
        for element in soup.find_all():
            if not element.get_text(strip=True) and not element.find(['img', 'svg']):
                element.decompose()
        
        return soup
    
    def _normalize_html_structure(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Normalize HTML structure: flatten dropdowns, normalize text extraction."""
        # Replace <br> with newlines for better text extraction
        for br in soup.find_all('br'):
            br.replace_with('\n')
        
        # Remove empty spans
        for span in soup.find_all('span'):
            if not span.get_text(strip=True) and not span.find(['img', 'svg']):
                span.unwrap()
        
        # Convert nested <p> inside <td> to separate blocks
        for td in soup.find_all('td'):
            for p in td.find_all('p'):
                p.insert_after('\n')
        
        return soup
    
    def parse_blocks(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse HTML into structured blocks."""
        blocks = []
        
        # Find main content area (ELMA365 specific)
        main_content = self._find_main_content(soup)
        if not main_content:
            main_content = soup.find('body') or soup
        
        # Process elements recursively - not just direct children
        # This handles cases where content is nested in sections, divs, etc.
        blocks = self._parse_recursive(main_content)
        
        return blocks
    
    def _parse_recursive(self, element: Tag) -> List[Dict]:
        """Recursively parse element and its children into blocks."""
        blocks = []
        
        # Process direct children first
        for child in element.children:
            if isinstance(child, Tag):
                # For container elements (div, section), always recurse to find content
                if child.name in ['div', 'section']:
                    # Always recursively process children of div/section
                    # This ensures we find content nested inside
                    child_blocks = self._parse_recursive(child)
                    if child_blocks:
                        blocks.extend(child_blocks)
                    else:
                        # If no blocks found recursively, try parsing the element itself
                        # (might be a special block or have direct content)
                        block = self._parse_element(child)
                        if block:
                            if isinstance(block, list):
                                blocks.extend(block)
                            else:
                                blocks.append(block)
                else:
                    # For other elements, parse directly
                    block = self._parse_element(child)
                    if block:
                        if isinstance(block, list):
                            blocks.extend(block)
                        else:
                            blocks.append(block)
        
        return blocks
    
    def _find_main_content(self, soup: BeautifulSoup) -> Optional[Tag]:
        """Find main content area with ELMA365 priority."""
        # ELMA365 specific: article.article .content
        elma_content = soup.select_one('article.article .content')
        if elma_content:
            return elma_content
        
        # Try common content selectors
        selectors = [
            'article.article',
            'main',
            'article',
            '.content',
            '.main-content',
            '#content',
            '.article-content',
            '[role="main"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element
        
        return None
    
    def _parse_element(self, element: Tag) -> Optional[Union[Dict, List[Dict]]]:
        """Parse a single element into block(s)."""
        tag_name = element.name.lower() if element.name else ''
        
        # Check for ELMA365 p_HeadingX classes
        classes = element.get('class', [])
        heading_class = None
        for cls in classes:
            if cls.startswith('p_Heading'):
                heading_class = cls
                break
        
        # Headers (including p_HeadingX)
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] or heading_class:
            if heading_class:
                # Extract level from p_HeadingX
                match = re.search(r'Heading(\d+)', heading_class)
                level = int(match.group(1)) if match else 3
            else:
                level = int(tag_name[1])
            
            text = self._extract_text_normalized(element)
            element_id = element.get('id', '')
            
            # Check if this is a tab header
            is_tab = False
            if text:
                # Check for tab pattern: "Вкладка «...»" or "Tab «...»"
                tab_match = re.search(r'(вкладка|tab)\s*[«"]([^»"]+)[»"]', text, re.I)
                if tab_match:
                    is_tab = True
            
            if text:
                # Generate ID if not provided
                if not element_id:
                    element_id = self._generate_header_id(text)
                
                header_block = {
                    'type': 'header',
                    'level': level,
                    'text': text,
                    'id': element_id
                }
                # Mark as tab if detected
                if is_tab:
                    header_block['kind'] = 'tab'
                return header_block
        
        # Dropdown blocks - extract as header + content
        if 'dropdown-toggle' in str(classes):
            return self._parse_dropdown(element)
        
        # Paragraphs
        elif tag_name == 'p':
            # Check for ELMA365 code blocks
            if 'p_CodeExample' in str(classes):
                return self._parse_elma_code_block(element)
            
            # Parse paragraph with inline links
            return self._parse_paragraph_with_links(element)
        
        # Code blocks (standard)
        elif tag_name in ['pre', 'code']:
            if tag_name == 'pre':
                code_element = element.find('code')
                if code_element:
                    code = code_element.get_text()
                    language = self._detect_language(code_element)
                else:
                    code = element.get_text()
                    language = None
            else:
                code = element.get_text()
                language = self._detect_language(element)
            
            if code.strip():
                return {
                    'type': 'code_block',
                    'language': language,
                    'code': code
                }
        
        # ELMA365 code blocks in spans
        elif tag_name == 'span' and 'f_CodeExample' in str(classes):
            code = self._extract_text_normalized(element)
            if code.strip():
                return {
                    'type': 'code_block',
                    'language': None,
                    'code': code
                }
        
        # Tables
        elif tag_name == 'table':
            return self._parse_table(element)
        
        # Lists
        elif tag_name in ['ul', 'ol']:
            return self._parse_list_with_links(element, tag_name == 'ol')
        
        # Images
        elif tag_name == 'img':
            return self._parse_image(element)
        
        # Links (extract text, optionally create link block)
        elif tag_name == 'a':
            href = element.get('href', '')
            text = self._extract_text_normalized(element)
            if text and href and not href.startswith('#'):
                # For now, just return text (link info can be added later)
                return {
                    'type': 'paragraph',
                    'text': text
                }
        
        # Divs and sections - process children
        elif tag_name in ['div', 'section', 'article', 'main']:
            # Check if it has meaningful content
            text = self._extract_text_normalized(element)
            if text:
                # Process children recursively
                child_blocks = []
                for child in element.children:
                    if isinstance(child, Tag):
                        child_block = self._parse_element(child)
                        if child_block:
                            if isinstance(child_block, list):
                                child_blocks.extend(child_block)
                            else:
                                child_blocks.append(child_block)
                
                if child_blocks:
                    return child_blocks
        
        return None
    
    def _parse_dropdown(self, element: Tag) -> Optional[List[Dict]]:
        """Parse dropdown block: extract toggle as header, body as content."""
        blocks = []
        
        # Extract toggle text as header
        toggle_text = self._extract_text_normalized(element)
        if toggle_text:
            blocks.append({
                'type': 'header',
                'level': 3,
                'text': toggle_text
            })
        
        # Find dropdown body - look in parent's children
        parent = element.parent
        if parent:
            found_toggle = False
            for sibling in parent.children:
                if sibling == element:
                    found_toggle = True
                    continue
                if found_toggle and isinstance(sibling, Tag):
                    classes = sibling.get('class', [])
                    if any('dropdown-toggle-body' in str(c) for c in classes):
                        body_text = self._extract_text_normalized(sibling)
                        if body_text:
                            blocks.append({
                                'type': 'paragraph',
                                'text': body_text
                            })
                        break
                    # Also check next siblings of parent
                    if sibling.name and sibling.name.startswith('h'):
                        break
        
        return blocks if blocks else None
    
    def _parse_elma_code_block(self, element: Tag) -> Optional[Dict]:
        """Parse ELMA365 code block from p_CodeExample."""
        # Find code span inside
        code_span = element.find('span', class_=re.compile(r'f_CodeExample'))
        if code_span:
            code = code_span.get_text()
        else:
            code = element.get_text()
        
        if code.strip():
            return {
                'type': 'code_block',
                'language': None,
                'code': code
            }
        return None
    
    def _parse_table(self, element: Tag) -> Optional[Dict]:
        """Parse table into structured format with header and rows as objects."""
        rows = []
        for tr in element.find_all('tr'):
            cells = []
            for td in tr.find_all(['td', 'th']):
                cell_text = self._extract_text_normalized(td)
                # Try to split cell if it contains enumeration
                cell_value = self._parse_cell_value(cell_text)
                cells.append(cell_value)
            if cells:
                rows.append(cells)
        
        if not rows:
            return None
        
        # Check if table is just a container (single cell with content)
        if len(rows) == 1 and len(rows[0]) == 1:
            # Try to split if it's a single cell with multiple values
            cell_value = rows[0][0]
            if isinstance(cell_value, str) and len(cell_value) > 100:
                # Try to detect if it's a merged cell that should be split
                split_cells = self._try_split_merged_cell(cell_value)
                if split_cells and len(split_cells) > 1:
                    # Create a proper table structure
                    return {
                        'type': 'table',
                        'header': [],
                        'rows': [split_cells]
                    }
            # Flatten: return as paragraph
            return {
                'type': 'paragraph',
                'text': cell_value if isinstance(cell_value, str) else str(cell_value)
            }
        
        # Determine header
        header = []
        data_rows = rows
        
        # Check if first row is header (all cells are text and short, not arrays)
        if rows:
            first_row = rows[0]
            is_header = all(
                isinstance(cell, str) and 
                len(cell) < 100 and 
                not any(char in cell for char in ['.', '!', '?']) and
                len(cell.split()) < 10
                for cell in first_row
            ) and len(first_row) > 1
            
            if is_header and len(first_row) > 1:
                header = first_row
                data_rows = rows[1:]
            else:
                header = []
                data_rows = rows
        
        # Convert rows to objects if header exists
        if header:
            table_rows = []
            for row in data_rows:
                if len(row) == len(header):
                    row_obj = {}
                    for i, col_name in enumerate(header):
                        row_obj[col_name] = row[i] if i < len(row) else ''
                    table_rows.append(row_obj)
                else:
                    # Fallback to array if column count doesn't match
                    table_rows.append(row)
            
            return {
                'type': 'table',
                'header': header,
                'rows': table_rows
            }
        else:
            return {
                'type': 'table',
                'header': [],
                'rows': data_rows
            }
    
    def _parse_cell_value(self, cell_text: str) -> Union[str, List[str]]:
        """Parse cell value, splitting enumerations into arrays."""
        if not cell_text:
            return ''
        
        # Check if it's an enumeration
        # Patterns: comma, semicolon, or long enumeration
        separators = [',', ';', ' и ', ' и\n', '\n']
        
        # Try to split by common separators
        for sep in separators:
            if sep in cell_text:
                parts = [p.strip() for p in cell_text.split(sep) if p.strip()]
                # If we got multiple meaningful parts, return as array
                if len(parts) > 1 and all(len(p) > 2 for p in parts):
                    return parts
        
        return cell_text
    
    def _try_split_merged_cell(self, cell_text: str) -> Optional[List[str]]:
        """Try to split a merged cell by detecting separators."""
        # Look for patterns separated by dashes, colons, or other separators
        patterns = [
            r'[—–-]\s*',  # Em dash, en dash, hyphen
            r':\s+',  # Colon
            r'\n+',  # Newlines
        ]
        
        for pattern in patterns:
            parts = re.split(pattern, cell_text)
            if len(parts) > 1:
                parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 3]
                if len(parts) > 1:
                    return parts
        
        return None
    
    def _parse_image(self, element: Tag) -> Optional[Dict]:
        """Parse image, filtering decorative ones."""
        src = element.get('src', '')
        alt = element.get('alt', '')
        
        # Check if decorative
        if self._is_decorative_image(src):
            return None
        
        # Check if meaningful (has alt or reasonable size)
        # For now, we'll keep images with alt text or non-decorative paths
        if not alt and self._is_decorative_image(src):
            return None
        
        return {
            'type': 'image',
            'src': src,
            'alt': alt
        }
    
    def _is_decorative_image(self, src: str) -> bool:
        """Check if image is decorative."""
        for pattern in self.DECORATIVE_IMAGE_PATTERNS:
            if re.search(pattern, src, re.I):
                return True
        return False
    
    def _parse_paragraph_with_links(self, element: Tag) -> Optional[Dict]:
        """Parse paragraph with inline links preserved as children."""
        children = self._extract_children_with_links(element)
        if not children:
            return None
        
        # If no links, return simple paragraph
        has_links = any(isinstance(c, dict) and c.get('type') == 'link' for c in children)
        if not has_links:
            # Combine all text
            text = ''.join(c if isinstance(c, str) else c.get('text', '') for c in children)
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                return {
                    'type': 'paragraph',
                    'text': text
                }
            return None
        
        # Return paragraph with children
        return {
            'type': 'paragraph',
            'children': children
        }
    
    def _parse_list_with_links(self, element: Tag, ordered: bool) -> Optional[Dict]:
        """Parse list with inline links preserved in items."""
        items = []
        for li in element.find_all('li', recursive=False):
            item_children = self._extract_children_with_links(li)
            if not item_children:
                continue
            
            # Clean item text (remove trailing ;, ., .)
            cleaned_children = self._clean_list_item_children(item_children)
            
            # If no links, use simple text
            has_links = any(isinstance(c, dict) and c.get('type') == 'link' for c in cleaned_children)
            if not has_links:
                text = ''.join(c if isinstance(c, str) else c.get('text', '') for c in cleaned_children)
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    items.append(text)
            else:
                items.append(cleaned_children)
        
        if items:
            return {
                'type': 'list',
                'ordered': ordered,
                'items': items
            }
        return None
    
    def _extract_children_with_links(self, element: Tag) -> List[Union[str, Dict]]:
        """Extract children preserving links as separate objects."""
        children = []
        
        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    children.append(text)
            elif isinstance(child, Tag):
                if child.name == 'a':
                    # Extract link
                    href = child.get('href', '')
                    text = child.get_text(strip=True)
                    if text and href:
                        # Normalize URL
                        target = self._normalize_url(href)
                        children.append({
                            'type': 'link',
                            'text': text,
                            'target': target
                        })
                    elif text:
                        # Link without href, just text
                        children.append(text)
                elif child.name in ['br']:
                    children.append(' ')
                else:
                    # Recursively process nested elements
                    nested_children = self._extract_children_with_links(child)
                    children.extend(nested_children)
        
        return children
    
    def _normalize_url(self, href: str) -> str:
        """Normalize URL to clean path or absolute URL."""
        if not href:
            return ''
        
        # If already absolute URL, return as is
        if href.startswith('http://') or href.startswith('https://'):
            return href
        
        # Remove fragments
        if '#' in href:
            href = href.split('#')[0]
        
        # Normalize relative paths
        if href.startswith('/'):
            return href
        
        # If relative path, ensure it starts with /
        if not href.startswith('/'):
            return '/' + href
        
        return href
    
    def _clean_list_item_children(self, children: List[Union[str, Dict]]) -> List[Union[str, Dict]]:
        """Remove trailing ;, ., . from list item children."""
        if not children:
            return children
        
        # Clean last text element
        last_idx = len(children) - 1
        if isinstance(children[last_idx], str):
            text = children[last_idx]
            # Remove trailing ;, ., .
            text = re.sub(r'[;\.]+$', '', text).strip()
            if text:
                children[last_idx] = text
            else:
                children.pop()
        elif isinstance(children[last_idx], dict) and children[last_idx].get('type') == 'link':
            # If last is link, check text before it
            if last_idx > 0 and isinstance(children[last_idx - 1], str):
                text = children[last_idx - 1]
                text = re.sub(r'[;\.]+$', '', text).strip()
                if text:
                    children[last_idx - 1] = text
                else:
                    children.pop(last_idx - 1)
        
        return children
    
    def _generate_header_id(self, text: str) -> str:
        """Generate unique header ID using slugify."""
        # Convert to ASCII
        slug = unidecode(text)
        # Convert to lowercase
        slug = slug.lower()
        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')
        
        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while slug in self._header_ids:
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        self._header_ids.add(slug)
        return slug
    
    def _remove_special_block_markers(self, soup: BeautifulSoup):
        """Remove special block markers from soup."""
        # Only remove elements that are clearly markers (short text, specific patterns)
        # Don't remove containers (div, section) that might have content
        for element in soup.find_all(['p', 'span']):
            text = element.get_text(strip=True).lower()
            # Only remove if it's a short marker text (not a full paragraph with content)
            if len(text) < 50:  # Markers are usually short
                if re.search(r'начало\s*(внимание|attention|примера|пример|важно)', text, re.I):
                    element.decompose()
                elif re.search(r'конец\s*(внимание|attention|примера|пример|важно)', text, re.I):
                    element.decompose()
    
    def _extract_breadcrumbs_from_url(self, url: str) -> List[str]:
        """Extract breadcrumbs from URL path."""
        try:
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            if not path:
                return []
            
            # Split path and filter out common segments
            segments = [s for s in path.split('/') if s and s not in ['ru', 'help', 'en']]
            return segments
        except Exception:
            return []
    
    def _add_semantic_roles(self, blocks: List[Dict]) -> List[Dict]:
        """Add semantic roles to blocks."""
        for block in blocks:
            block_type = block.get('type')
            text = self._get_block_text(block)
            
            if block_type == 'header':
                block['semantic_role'] = 'section'
            elif block_type == 'list':
                # Mark list items
                if 'items' in block:
                    block['semantic_role'] = 'list_item'
            elif block_type == 'special_block':
                kind = block.get('kind', '').lower()
                if kind == 'warning' or 'внимание' in kind or 'attention' in kind:
                    block['semantic_role'] = 'warning'
                elif kind == 'example' or 'пример' in kind:
                    block['semantic_role'] = 'example'
                elif kind == 'important' or 'важно' in kind:
                    block['semantic_role'] = 'important'
            elif block_type == 'paragraph':
                text_lower = text.lower()
                # Check for definition patterns
                if re.search(r'—\s*это\s+|представляет\s+собой|является\s+', text_lower):
                    block['semantic_role'] = 'definition'
                # Check for capability patterns
                elif re.search(r'позволяет|можно|возможность|возможен', text_lower):
                    block['semantic_role'] = 'capability'
                # Check for configuration patterns
                elif re.search(r'настройте|перейдите\s+в\s+раздел|в\s+разделе', text_lower):
                    block['semantic_role'] = 'configuration'
        
        return blocks
    
    def _add_token_counts(self, blocks: List[Dict]) -> List[Dict]:
        """Add token counts to blocks."""
        if not self.token_encoder:
            return blocks
        
        for block in blocks:
            text = self._get_block_text(block)
            if text:
                try:
                    tokens = self.token_encoder.encode(text)
                    block['token_count'] = len(tokens)
                except Exception:
                    block['token_count'] = 0
        
        return blocks
    
    def _extract_text_normalized(self, element: Tag) -> str:
        """Extract text with normalization: proper spacing, no inline elements."""
        # Use separator to avoid text sticking
        text = element.get_text(" ", strip=True)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _detect_language(self, code_element: Tag) -> Optional[str]:
        """Detect programming language from code element."""
        # Check class for language hint
        class_attr = code_element.get('class', [])
        for cls in class_attr:
            if cls.startswith('language-'):
                return cls.replace('language-', '')
            if cls.startswith('lang-'):
                return cls.replace('lang-', '')
        
        # Check data attributes
        lang = code_element.get('data-lang') or code_element.get('data-language')
        if lang:
            return lang
        
        return None
    
    def _filter_semantic_noise(self, blocks: List[Dict]) -> List[Dict]:
        """Filter out semantic noise blocks."""
        filtered = []
        
        for block in blocks:
            text = self._get_block_text(block)
            
            # Skip empty or very short blocks
            if not text or len(text) < 5:
                continue
            
            # Skip blocks starting with copyright
            if text.strip().startswith('©'):
                continue
            
            # Check for high link ratio
            if self._has_high_link_ratio(block):
                continue
            
            # Check stoplist patterns
            text_lower = text.lower()
            is_noise = False
            for pattern in self.SEMANTIC_NOISE_PATTERNS:
                if re.search(pattern, text_lower, re.I):
                    is_noise = True
                    break
            
            if not is_noise:
                filtered.append(block)
        
        return filtered
    
    def _get_block_text(self, block: Dict) -> str:
        """Extract text from block for filtering."""
        block_type = block.get('type')
        if block_type == 'paragraph':
            # Check if has children
            if 'children' in block:
                text_parts = []
                for child in block['children']:
                    if isinstance(child, str):
                        text_parts.append(child)
                    elif isinstance(child, dict) and child.get('type') == 'link':
                        text_parts.append(child.get('text', ''))
                return ' '.join(text_parts)
            return block.get('text', '')
        elif block_type == 'header':
            return block.get('text', '')
        elif block_type == 'list':
            items = block.get('items', [])
            text_parts = []
            for item in items:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, list):
                    # Item has children
                    for child in item:
                        if isinstance(child, str):
                            text_parts.append(child)
                        elif isinstance(child, dict) and child.get('type') == 'link':
                            text_parts.append(child.get('text', ''))
            return ' '.join(text_parts)
        elif block_type == 'code_block':
            return block.get('code', '')
        elif block_type == 'table':
            rows = block.get('rows', [])
            text_parts = []
            for row in rows:
                if isinstance(row, dict):
                    # Row is an object
                    text_parts.extend(str(v) for v in row.values())
                elif isinstance(row, list):
                    text_parts.extend(str(cell) for cell in row)
            return ' '.join(text_parts)
        elif block_type == 'special_block':
            # New format: text field
            if 'text' in block:
                return block.get('text', '')
            # Old format: content array
            content = block.get('content', [])
            if isinstance(content, list):
                return ' '.join(str(c.get('text', '')) if isinstance(c, dict) else str(c) for c in content)
            return ''
        return ''
    
    def _has_high_link_ratio(self, block: Dict) -> bool:
        """Check if block contains mostly links (navigation)."""
        text = self._get_block_text(block)
        # Simple heuristic: if text is very short and contains common link patterns
        if len(text) < 50:
            link_patterns = ['http://', 'https://', '.html', '/help/']
            link_count = sum(1 for pattern in link_patterns if pattern in text)
            if link_count > 0 and len(text.split()) < 10:
                return True
        return False
    
    def _validate_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """Validate and clean blocks."""
        validated = []
        prev_empty = False
        
        for block in blocks:
            # Skip blocks without type
            if not block.get('type'):
                continue
            
            # Skip empty blocks
            text = self._get_block_text(block)
            if not text.strip():
                continue
            
            # Skip consecutive empty paragraphs
            if block.get('type') == 'paragraph' and not text.strip():
                if prev_empty:
                    continue
                prev_empty = True
            else:
                prev_empty = False
            
            # Skip headers without text
            if block.get('type') == 'header' and not block.get('text', '').strip():
                continue
            
            # Skip empty lists
            if block.get('type') == 'list' and not block.get('items'):
                continue
            
            validated.append(block)
        
        return validated
    
    def _build_metadata(
        self,
        soup: BeautifulSoup,
        blocks: List[Dict],
        title: Optional[str],
        breadcrumbs: Optional[List[str]],
        special_blocks: List[Dict],
        source_url: Optional[str] = None
    ) -> Dict:
        """Build comprehensive metadata."""
        # Calculate word count
        word_count = 0
        for block in blocks:
            text = self._get_block_text(block)
            word_count += len(text.split())
        
        # Extract headers for structure map - simple array of header texts
        # Also include h1 from soup if available (main title)
        headers = []
        
        # Try to get h1 from soup (main document title)
        # Check in article header (ELMA365 structure) - even if it might be removed by boilerplate
        # Try multiple selectors
        h1_selectors = [
            'article.article .article__header h1',
            'article.article .topic__title h1',
            'article.article h1',
            'h1'
        ]
        
        h1_text = None
        for selector in h1_selectors:
            h1_elem = soup.select_one(selector)
            if h1_elem:
                h1_text = h1_elem.get_text(strip=True)
                if h1_text:
                    break
        
        if h1_text and h1_text not in headers:
            headers.append(h1_text)
        
        # Also try direct find as fallback
        if not headers:
            article_header = soup.select_one('article.article .article__header h1, article.article .topic__title h1')
            if article_header:
                h1_text = article_header.get_text(strip=True)
                if h1_text and h1_text not in headers:
                    headers.append(h1_text)
            else:
                # Fallback to any h1
                h1 = soup.find('h1')
                if h1:
                    h1_text = h1.get_text(strip=True)
                    if h1_text and h1_text not in headers:
                        headers.append(h1_text)
        
        # Then add all header blocks
        for block in blocks:
            if block.get('type') == 'header':
                header_text = block.get('text', '').strip()
                if header_text and header_text not in headers:
                    headers.append(header_text)
        
        # Count content images
        images_count = sum(1 for block in blocks if block.get('type') == 'image')
        
        metadata = {
            'title': title or self._extract_title(soup),
            'breadcrumbs': breadcrumbs or [],
            'extracted_at': datetime.now().isoformat(),
            'special_blocks_count': len(special_blocks),
            'word_count': word_count,
            'headers': headers,
            'images_count': images_count
        }
        
        # Add source_url if provided
        if source_url:
            metadata['source_url'] = source_url
        
        return metadata
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract title from cleaned soup."""
        # Try h1 in article header first (ELMA365 structure)
        article_header = soup.select_one('article.article .article__header h1, article.article .topic__title h1')
        if article_header:
            title = article_header.get_text(strip=True)
            if title:
                return title
        
        # Fallback to any h1
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
            if title:
                return title
        return None
    
    def _group_blocks_into_sections(self, blocks: List[Dict]) -> List[Dict]:
        """
        Group blocks into semantic sections based on headers and semantic markers.
        Each section has a title, type, and items.
        Creates intro section for blocks before first header.
        Also creates sections for distinct semantic groups (lists, tables, links).
        """
        sections = []
        current_section = None
        current_blocks = []
        intro_blocks = []
        found_first_header = False
        
        for block in blocks:
            block_type = block.get('type')
            
            # If we encounter a header, start a new section
            if block_type == 'header':
                # Save intro section if exists (blocks before first header)
                if not found_first_header and intro_blocks:
                    intro_section = self._build_section_data(None, intro_blocks)
                    if intro_section:
                        intro_section['title'] = ''  # Intro section has no title
                        sections.append(intro_section)
                    intro_blocks = []
                    found_first_header = True
                
                # Save previous section if exists
                if current_section:
                    section_data = self._build_section_data(current_section, current_blocks)
                    if section_data:
                        sections.append(section_data)
                
                # Start new section
                current_section = block
                current_blocks = []
            else:
                if found_first_header:
                    # Add block to current section
                    current_blocks.append(block)
                else:
                    # Collect intro blocks (before first header)
                    intro_blocks.append(block)
        
        # Save intro section if no headers were found
        if not found_first_header and intro_blocks:
            intro_section = self._build_section_data(None, intro_blocks)
            if intro_section:
                intro_section['title'] = ''
                sections.append(intro_section)
        
        # Don't forget the last section
        if current_section:
            section_data = self._build_section_data(current_section, current_blocks)
            if section_data:
                sections.append(section_data)
        
        # If no sections were created (no headers), 
        # try to create sections from semantic markers
        if not sections and blocks:
            sections = self._create_sections_from_semantic_markers(blocks)
        elif sections and not found_first_header:
            # If we have sections but no headers were found, 
            # try to create better semantic sections from all blocks
            # This handles cases where document has no explicit headers but has distinct semantic groups
            semantic_sections = self._create_sections_from_semantic_markers(blocks)
            if len(semantic_sections) > len(sections):
                # Use semantic sections if they provide better structure
                sections = semantic_sections
        
        return sections
    
    def _create_sections_from_semantic_markers(self, blocks: List[Dict]) -> List[Dict]:
        """
        Create sections from semantic markers when no headers are present.
        Groups blocks by type: intro text, lists, tables, links.
        """
        sections = []
        current_group = []
        current_group_type = None
        
        for block in blocks:
            block_type = block.get('type')
            
            # Determine if this block starts a new semantic group
            if block_type == 'table':
                # Save previous group
                if current_group:
                    section = self._build_section_data(None, current_group)
                    if section:
                        sections.append(section)
                    current_group = []
                
                # Table becomes its own section
                section = self._build_section_data(None, [block])
                if section:
                    sections.append(section)
            elif block_type == 'list':
                # Lists can be grouped together
                if current_group_type != 'list' and current_group:
                    # Save previous group
                    section = self._build_section_data(None, current_group)
                    if section:
                        sections.append(section)
                    current_group = []
                
                current_group.append(block)
                current_group_type = 'list'
            elif block_type == 'paragraph':
                # Check if paragraph contains mostly links
                children = block.get('children', [])
                has_links = any(isinstance(c, dict) and c.get('type') == 'link' for c in children)
                
                if has_links:
                    # Links section
                    if current_group_type != 'links' and current_group:
                        section = self._build_section_data(None, current_group)
                        if section:
                            sections.append(section)
                        current_group = []
                    current_group.append(block)
                    current_group_type = 'links'
                else:
                    # Regular paragraph - add to current group or start new
                    if current_group_type and current_group_type not in ['text', None]:
                        # Save previous group
                        section = self._build_section_data(None, current_group)
                        if section:
                            sections.append(section)
                        current_group = []
                    current_group.append(block)
                    current_group_type = 'text'
            else:
                # Other block types - add to current group
                current_group.append(block)
        
        # Save last group
        if current_group:
            section = self._build_section_data(None, current_group)
            if section:
                sections.append(section)
        
        return sections
    
    def _build_section_data(self, header_block: Optional[Dict], blocks: List[Dict]) -> Optional[Dict]:
        """
        Build section data from header and blocks.
        Determines section type and structures items.
        Infers section title from context if no header is provided.
        """
        if not blocks and not header_block:
            return None
        
        # Extract section title
        title = header_block.get('text', '') if header_block else None
        if not title:
            # Try to find title from first block
            for block in blocks:
                if block.get('type') == 'header':
                    title = block.get('text', '')
                    break
            
            # If still no title, try to infer from context
            if not title:
                title = self._infer_section_title(blocks)
        
        # Determine section type and extract items
        section_type, items = self._determine_section_type_and_items(blocks)
        
        # Skip empty sections
        if not items and not title:
            return None
        
        section = {
            'title': title or '',
            'type': section_type,
            'items': items
        }
        
        return section
    
    def _determine_section_type_and_items(self, blocks: List[Dict]) -> Tuple[str, List]:
        """
        Determine section type and extract structured items.
        Returns: (type, items)
        """
        if not blocks:
            return ('text', [])
        
        # Check for comparison table (table with 2+ columns, comparing options)
        for block in blocks:
            if block.get('type') == 'table':
                table = block
                header = table.get('header', [])
                rows = table.get('rows', [])
                
                # Check if it's a comparison table (has 2+ columns)
                is_comparison = False
                if header and len(header) >= 2:
                    is_comparison = True
                elif rows and len(rows) > 0:
                    first_row = rows[0]
                    if isinstance(first_row, dict) and len(first_row) >= 2:
                        is_comparison = True
                    elif isinstance(first_row, list) and len(first_row) >= 2:
                        is_comparison = True
                
                if is_comparison:
                    items = []
                    # Convert table rows to comparison items with name and benefits format
                    if header and rows:
                        # Table with header - convert to comparison format
                        for col_idx, col_name in enumerate(header):
                            # Each column becomes a comparison item
                            comparison_item = {
                                'name': col_name,
                                'benefits': []
                            }
                            
                            # Collect all benefits from this column
                            for row in rows:
                                if isinstance(row, list) and col_idx < len(row):
                                    cell_value = row[col_idx]
                                    if isinstance(cell_value, list):
                                        # Cell contains list of benefits
                                        for benefit in cell_value:
                                            if benefit and str(benefit).strip():
                                                comparison_item['benefits'].append(str(benefit).strip())
                                    elif cell_value and str(cell_value).strip():
                                        # Single benefit
                                        comparison_item['benefits'].append(str(cell_value).strip())
                                elif isinstance(row, dict) and col_name in row:
                                    cell_value = row[col_name]
                                    if isinstance(cell_value, list):
                                        for benefit in cell_value:
                                            if benefit and str(benefit).strip():
                                                comparison_item['benefits'].append(str(benefit).strip())
                                    elif cell_value and str(cell_value).strip():
                                        comparison_item['benefits'].append(str(cell_value).strip())
                            
                            if comparison_item['benefits']:
                                items.append(comparison_item)
                    elif rows and not header:
                        # Table without header - check if first row looks like header
                        if rows and isinstance(rows[0], list) and len(rows[0]) >= 2:
                            # Use first row as header
                            potential_header = rows[0]
                            # Check if first row looks like header (short text, no punctuation)
                            looks_like_header = all(
                                isinstance(cell, str) and 
                                len(cell) < 50 and 
                                not any(char in cell for char in ['.', '!', '?']) 
                                for cell in potential_header
                            )
                            if looks_like_header:
                                header = potential_header
                                # Convert to comparison format with name and benefits
                                for col_idx, col_name in enumerate(header):
                                    comparison_item = {
                                        'name': col_name,
                                        'benefits': []
                                    }
                                    # Collect benefits from this column
                                    for row in rows[1:]:
                                        if isinstance(row, list) and col_idx < len(row):
                                            cell_value = row[col_idx]
                                            if isinstance(cell_value, list):
                                                for benefit in cell_value:
                                                    if benefit and str(benefit).strip():
                                                        comparison_item['benefits'].append(str(benefit).strip())
                                            elif cell_value and str(cell_value).strip():
                                                comparison_item['benefits'].append(str(cell_value).strip())
                                    if comparison_item['benefits']:
                                        items.append(comparison_item)
                            else:
                                # No header, convert rows to dicts with generic keys
                                for i, row in enumerate(rows):
                                    if isinstance(row, dict):
                                        items.append(row)
                                    elif isinstance(row, list):
                                        row_obj = {}
                                        for j, cell in enumerate(row):
                                            row_obj[f'column_{j+1}'] = cell
                                        items.append(row_obj)
                        elif rows and isinstance(rows[0], dict):
                            # Already dict format
                            items = rows
                    
                    if items:
                        return ('comparison', items)
        
        # Check for links section (mostly links or paragraphs with links)
        link_count = 0
        total_blocks = 0
        link_items = []
        
        for block in blocks:
            block_type = block.get('type')
            total_blocks += 1
            
            if block_type == 'paragraph':
                children = block.get('children', [])
                if children:
                    # Check if paragraph contains links
                    has_links = any(isinstance(c, dict) and c.get('type') == 'link' for c in children)
                    if has_links:
                        link_count += 1
                        # Extract link from paragraph
                        for child in children:
                            if isinstance(child, dict) and child.get('type') == 'link':
                                link_items.append({
                                    'label': child.get('text', ''),
                                    'url': child.get('target', '')
                                })
            elif block_type == 'list':
                items = block.get('items', [])
                for item in items:
                    if isinstance(item, list):
                        # Check if item contains links
                        for child in item:
                            if isinstance(child, dict) and child.get('type') == 'link':
                                link_items.append({
                                    'label': child.get('text', ''),
                                    'url': child.get('target', '')
                                })
                                link_count += 1
        
        # If more than 50% of blocks contain links, it's a links section
        if link_count > 0 and (link_count / max(total_blocks, 1)) > 0.5:
            if link_items:
                return ('links', link_items)
        
        # Check for list section (mostly lists)
        list_blocks = [b for b in blocks if b.get('type') == 'list']
        if len(list_blocks) > len(blocks) * 0.5:
            # Extract all list items
            all_items = []
            for list_block in list_blocks:
                items = list_block.get('items', [])
                for item in items:
                    if isinstance(item, str):
                        all_items.append(item)
                    elif isinstance(item, list):
                        # Extract text from children
                        text_parts = []
                        for child in item:
                            if isinstance(child, str):
                                text_parts.append(child)
                            elif isinstance(child, dict) and child.get('type') == 'link':
                                text_parts.append(child.get('text', ''))
                        if text_parts:
                            all_items.append(''.join(text_parts))
            if all_items:
                return ('list', all_items)
        
        # Default: text section - extract plain text from all blocks
        text_items = []
        for block in blocks:
            text = self._extract_plain_text_from_block(block)
            if text and text.strip():
                text_items.append(text)
        
        return ('text', text_items)
    
    def _remove_duplicate_tables_from_blocks(self, blocks: List[Dict], sections: List[Dict]) -> List[Dict]:
        """
        Remove table blocks from blocks list if they're already represented in sections.
        This avoids duplication - sections have semantic structure, blocks keep original structure.
        """
        # Find all table blocks that are in comparison sections
        table_blocks_to_remove = set()
        
        for section in sections:
            if section.get('type') == 'comparison':
                # This section contains a table - find and mark corresponding table block
                for i, block in enumerate(blocks):
                    if block.get('type') == 'table':
                        # Check if this table matches the comparison section
                        # (simple heuristic: if it's a comparison section, remove the table)
                        table_blocks_to_remove.add(i)
        
        # Remove marked blocks
        if table_blocks_to_remove:
            filtered_blocks = [block for i, block in enumerate(blocks) if i not in table_blocks_to_remove]
            return filtered_blocks
        
        return blocks
    
    def _infer_section_title(self, blocks: List[Dict]) -> str:
        """
        Infer section title from context.
        Analyzes blocks to determine semantic meaning.
        """
        if not blocks:
            return ''
        
        # Check first paragraph for common patterns
        first_block = blocks[0]
        if first_block.get('type') == 'paragraph':
            text = first_block.get('text', '')
            if not text and 'children' in first_block:
                text = ''.join(str(c) if isinstance(c, str) else c.get('text', '') for c in first_block['children'])
            
            # Common patterns for section titles in text
            patterns = {
                r'вариант[ы]? поставк': 'Варианты поставки',
                r'редакци[ия]': 'Редакции',
                r'дополнительн': 'Дополнительные материалы',
                r'ссылки|материалы|читайте|подробнее': 'Дополнительные материалы',
                r'сравнен': 'Сравнение',
            }
            
            text_lower = text.lower()
            for pattern, inferred_title in patterns.items():
                if re.search(pattern, text_lower):
                    return inferred_title
        
        # Check if section is a list with specific content
        list_blocks = [b for b in blocks if b.get('type') == 'list']
        if list_blocks:
            first_list = list_blocks[0]
            items = first_list.get('items', [])
            if items:
                first_item = str(items[0]).lower()
                if 'saas' in first_item or 'on-premises' in first_item:
                    return 'Варианты поставки'
                if 'standard' in first_item or 'enterprise' in first_item:
                    return 'Редакции'
        
        # Check if section is comparison
        table_blocks = [b for b in blocks if b.get('type') == 'table']
        if table_blocks:
            return 'Сравнение поставок'
        
        # Check if section is links
        link_count = 0
        for block in blocks:
            if block.get('type') == 'paragraph' and 'children' in block:
                if any(isinstance(c, dict) and c.get('type') == 'link' for c in block['children']):
                    link_count += 1
        if link_count > 0:
            return 'Дополнительные материалы'
        
        return ''
    
    def _extract_plain_text_from_block(self, block: Dict) -> str:
        """Extract plain text from a single block."""
        block_type = block.get('type')
        
        if block_type == 'header':
            return block.get('text', '')
        elif block_type == 'paragraph':
            if 'children' in block:
                text_parts = []
                for child in block['children']:
                    if isinstance(child, str):
                        text_parts.append(child)
                    elif isinstance(child, dict) and child.get('type') == 'link':
                        text_parts.append(child.get('text', ''))
                return ''.join(text_parts)
            else:
                return block.get('text', '')
        elif block_type == 'list':
            items = block.get('items', [])
            text_parts = []
            for item in items:
                if isinstance(item, str):
                    text_parts.append(f"• {item}")
                elif isinstance(item, list):
                    item_text = ''
                    for child in item:
                        if isinstance(child, str):
                            item_text += child
                        elif isinstance(child, dict) and child.get('type') == 'link':
                            item_text += child.get('text', '')
                    if item_text:
                        text_parts.append(f"• {item_text}")
            return '\n'.join(text_parts)
        elif block_type == 'code_block':
            return block.get('code', '')
        elif block_type == 'table':
            rows = block.get('rows', [])
            header = block.get('header', [])
            text_parts = []
            
            if header:
                text_parts.append(' | '.join(header))
            
            for row in rows:
                if isinstance(row, dict):
                    row_text = ' | '.join(str(v) for v in row.values())
                    text_parts.append(row_text)
                elif isinstance(row, list):
                    row_text = ' | '.join(str(cell) for cell in row)
                    text_parts.append(row_text)
            
            return '\n'.join(text_parts)
        elif block_type == 'special_block':
            return block.get('text', '') or block.get('heading', '')
        
        return ''
    
    def _extract_plain_text_from_sections(self, sections: List[Dict]) -> str:
        """
        Extract canonical plain text from sections.
        Includes ALL sections including intro section (with empty title).
        No HTML, clean structured text.
        """
        text_parts = []
        
        for section in sections:
            title = section.get('title', '')
            # Include section title if it exists (intro section has empty title)
            if title:
                text_parts.append(title)
                text_parts.append('')  # Empty line after title
            
            section_type = section.get('type', '')
            items = section.get('items', [])
            
            if section_type == 'comparison':
                # Format comparison table as text (name: benefit1, benefit2, ...)
                for item in items:
                    if isinstance(item, dict):
                        name = item.get('name', '')
                        benefits = item.get('benefits', [])
                        if name and benefits:
                            benefits_str = ', '.join(str(b) for b in benefits if b)
                            text_parts.append(f"{name}: {benefits_str}")
                        elif name:
                            # Fallback for old format
                            item_parts = []
                            for k, v in item.items():
                                if k != 'name' and v:
                                    if isinstance(v, list):
                                        v_str = ', '.join(str(x) for x in v if x)
                                        item_parts.append(f"{k}: {v_str}")
                                    else:
                                        item_parts.append(f"{k}: {v}")
                            if item_parts:
                                text_parts.append(f"{name}: {' | '.join(item_parts)}")
                    elif isinstance(item, list):
                        # Handle list cells (old format)
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
                        # Format dict as text
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
            
            # Add empty line between sections (but not after last section)
            if section != sections[-1]:
                text_parts.append('')
        
        result = '\n'.join(text_parts).strip()
        
        # If result is too short, try to extract from blocks as fallback
        # This ensures we don't lose content
        if len(result) < 100 and sections:
            # Fallback: extract from all blocks in sections
            all_text_parts = []
            for section in sections:
                items = section.get('items', [])
                section_type = section.get('type', '')
                
                if section_type == 'text':
                    all_text_parts.extend(items)
                elif section_type == 'list':
                    all_text_parts.extend([f"• {item}" if isinstance(item, str) else str(item) for item in items])
                elif section_type == 'comparison':
                    for item in items:
                        if isinstance(item, dict):
                            name = item.get('name', '')
                            benefits = item.get('benefits', [])
                            if name and benefits:
                                all_text_parts.append(f"{name}: {', '.join(str(b) for b in benefits)}")
                elif section_type == 'links':
                    for item in items:
                        if isinstance(item, dict):
                            label = item.get('label', '')
                            if label:
                                all_text_parts.append(label)
            
            if all_text_parts:
                fallback_result = '\n'.join(all_text_parts).strip()
                if len(fallback_result) > len(result):
                    result = fallback_result
        
        return result