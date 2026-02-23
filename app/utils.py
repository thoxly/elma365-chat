import re
import uuid
from urllib.parse import urlparse, urljoin
from typing import Optional, List, Dict, Any


def extract_doc_id(url: str) -> str:
    """
    Extract doc_id from URL.
    Patterns:
    - /help/platform/how_to_bind_app_to_proccess.html -> how_to_bind_app_to_proccess
    - /help/platform/360008121732.html -> 360008121732
    - Fallback to UUID if no pattern matches
    """
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    
    # Try to extract from filename (without extension)
    if path.endswith('.html'):
        # Remove .html extension
        path = path[:-5]
        # Extract last segment
        segments = path.split('/')
        if segments:
            last_segment = segments[-1]
            # Check if it's a valid identifier (alphanumeric, underscores, hyphens)
            if re.match(r'^[a-zA-Z0-9_-]+$', last_segment):
                return last_segment
    
    # Try to extract numeric ID
    numeric_match = re.search(r'/(\d+)\.html', url)
    if numeric_match:
        return numeric_match.group(1)
    
    # Try to extract from path segments (e.g., how_to_bind_app_to_proccess)
    if path:
        segments = path.split('/')
        for segment in reversed(segments):
            if segment and re.match(r'^[a-zA-Z0-9_-]+$', segment):
                return segment
    
    # Fallback to UUID
    return str(uuid.uuid4())


def normalize_url(url: str, base_url: str) -> str:
    """Normalize URL to absolute URL."""
    if url.startswith('http://') or url.startswith('https://'):
        return url
    return urljoin(base_url, url)


def normalize_path(url: str) -> str:
    """
    Normalize URL path for navigation and linking.
    
    Rules:
    1. Remove domain: https://elma365.com/ru/help/... -> /ru/help/...
    2. Remove leading /{lang}/help prefix: /ru/help/business_solutions/... -> business_solutions/...
    3. Convert to lowercase
    4. Remove query parameters (? and #)
    
    Example:
        https://elma365.com/ru/help/business_solutions/create-plan.html?param=value#anchor
        -> business_solutions/create-plan.html
    """
    # Parse URL to extract path
    parsed = urlparse(url)
    path = parsed.path
    
    # Remove leading /{lang}/help/ pattern (e.g., /ru/help/, /en/help/)
    # Pattern: /{lang}/help/... or /help/...
    if '/help/' in path:
        help_index = path.find('/help/')
        if help_index != -1:
            # Get path after /help/
            path = path[help_index + len('/help/'):]
    
    # Remove leading and trailing slashes
    path = path.strip('/')
    
    # Convert to lowercase
    path = path.lower()
    
    # Return normalized path (already removed query and fragment via urlparse)
    return path


def extract_outgoing_links(blocks: List[Dict[str, Any]]) -> List[str]:
    """
    Extract all outgoing links from normalized blocks and return as list of normalized paths.
    
    Args:
        blocks: List of normalized blocks (from content.blocks)
    
    Returns:
        List of normalized paths (e.g., ['crm/create-lead.html', 'platform/widget.html'])
    """
    outgoing_links = set()  # Use set to avoid duplicates
    
    def extract_from_block(block: Dict[str, Any]):
        """Recursively extract links from a block."""
        block_type = block.get('type')
        
        if block_type == 'paragraph' and 'children' in block:
            # Extract links from children array
            for child in block.get('children', []):
                if isinstance(child, dict) and child.get('type') == 'link':
                    target = child.get('target', '')
                    if target:
                        # Normalize the target URL
                        normalized = normalize_path(target)
                        if normalized:  # Only add non-empty normalized paths
                            outgoing_links.add(normalized)
        
        elif block_type == 'list' and 'items' in block:
            # Extract links from list items
            for item in block.get('items', []):
                if isinstance(item, list):
                    # Item is a children array
                    for child in item:
                        if isinstance(child, dict) and child.get('type') == 'link':
                            target = child.get('target', '')
                            if target:
                                normalized = normalize_path(target)
                                if normalized:
                                    outgoing_links.add(normalized)
                elif isinstance(item, str):
                    # Plain text item, skip
                    pass
    
    # Process all blocks
    for block in blocks:
        extract_from_block(block)
    
    # Return as sorted list for consistency
    return sorted(list(outgoing_links))


def is_valid_help_url(url: str, base_url: str, platform_only: bool = False) -> bool:
    """
    Check if URL is a valid help documentation URL.
    Supports both /help/ and /{lang}/help/ patterns (e.g., /ru/help/, /en/help/).
    
    Args:
        url: URL to check
        base_url: Base URL for domain validation
        platform_only: If True, only accept URLs under /ru/help/platform/
    """
    parsed = urlparse(url)
    base_parsed = urlparse(base_url)
    
    # Must be same domain
    if parsed.netloc and parsed.netloc != base_parsed.netloc:
        return False
    
    path = parsed.path
    
    # Must be under /help/ path (with or without language prefix)
    # Patterns: /help/... or /{lang}/help/... (e.g., /ru/help/...)
    if '/help/' not in path:
        return False
    
    # Extract the part after /help/
    help_index = path.find('/help/')
    if help_index == -1:
        return False
    
    # Get path after /help/
    path_after_help = path[help_index + len('/help/'):]
    
    # If platform_only is True, check that path starts with platform/
    if platform_only:
        if not path_after_help.startswith('platform/'):
            return False
    
    # Skip empty paths and root paths
    if not path_after_help or path_after_help == '/':
        return False
    
    # Should be HTML page (ends with .html) or a valid article path
    # Accept both .html files and paths that look like article URLs
    if path.endswith('.html'):
        return True
    
    # Also accept paths that don't end with / (non-directory paths)
    # This helps catch article URLs that might not have .html extension
    if not path.endswith('/'):
        # Check if it looks like an article path (has some content after /help/)
        if path_after_help and len(path_after_help.strip('/')) > 0:
            return True
    
    return False
