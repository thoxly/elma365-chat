from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from urllib.parse import urljoin, urlparse
import re


class HTMLParser:
    """Parser for extracting data from ELMA365 documentation pages."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def parse(self, html: str, url: str) -> Dict:
        """Parse HTML and extract all relevant data."""
        soup = BeautifulSoup(html, 'lxml')
        
        return {
            'title': self.extract_title(soup),
            'breadcrumbs': self.extract_breadcrumbs(soup),
            'section': self.extract_section(url, soup),
            'html': str(soup),
            'plain_text': self.extract_plain_text(soup),
            'links': self.extract_links(soup, url)
        }
    
    def extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page title."""
        # Try h1 first
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        # Try title tag
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        # Try meta title
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            return meta_title.get('content')
        
        return None
    
    def extract_breadcrumbs(self, soup: BeautifulSoup) -> List[str]:
        """Extract breadcrumb navigation."""
        breadcrumbs = []
        
        # Look for common breadcrumb patterns
        # Pattern 1: nav with breadcrumb class
        breadcrumb_nav = soup.find('nav', class_=re.compile(r'breadcrumb', re.I))
        if breadcrumb_nav:
            links = breadcrumb_nav.find_all('a')
            for link in links:
                text = link.get_text(strip=True)
                if text:
                    breadcrumbs.append(text)
        
        # Pattern 2: ol/ul with breadcrumb class
        breadcrumb_list = soup.find(['ol', 'ul'], class_=re.compile(r'breadcrumb', re.I))
        if breadcrumb_list:
            items = breadcrumb_list.find_all(['li', 'a'])
            for item in items:
                text = item.get_text(strip=True)
                if text and text not in breadcrumbs:
                    breadcrumbs.append(text)
        
        # Pattern 3: Look for structured data
        breadcrumb_script = soup.find('script', type='application/ld+json')
        if breadcrumb_script:
            try:
                import json
                data = json.loads(breadcrumb_script.string)
                if isinstance(data, dict) and 'itemListElement' in data:
                    for item in data['itemListElement']:
                        if 'name' in item:
                            breadcrumbs.append(item['name'])
            except:
                pass
        
        return breadcrumbs
    
    def extract_section(self, url: str, soup: BeautifulSoup) -> str:
        """Extract section information (breadcrumbs + URL segment)."""
        breadcrumbs = self.extract_breadcrumbs(soup)
        url_segment = self._extract_url_segment(url)
        
        parts = []
        if breadcrumbs:
            parts.append(' > '.join(breadcrumbs))
        if url_segment:
            parts.append(f"[{url_segment}]")
        
        return ' | '.join(parts) if parts else url_segment or ''
    
    def _extract_url_segment(self, url: str) -> str:
        """Extract section segment from URL."""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        # Extract segment after /help/
        if '/help/' in path:
            parts = path.split('/help/')
            if len(parts) > 1:
                segment = parts[1].split('/')[0]
                return segment
        
        return ''
    
    def extract_plain_text(self, soup: BeautifulSoup) -> str:
        """Extract plain text from HTML."""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text(separator=' ', strip=True)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def extract_links(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """
        Extract all links from the page.
        Focuses on finding documentation article links.
        """
        links = []
        seen_links = set()  # Avoid duplicates
        
        # Extract all anchor tags with href
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Skip empty, javascript, mailto, tel links
            if not href or href.startswith('javascript:') or href.startswith('mailto:') or href.startswith('tel:'):
                continue
            
            # Skip anchor links (fragments)
            if href.startswith('#'):
                continue
            
            # Normalize to absolute URL
            absolute_url = urljoin(current_url, href)
            
            # Remove fragment (#) from URL
            if '#' in absolute_url:
                absolute_url = absolute_url.split('#')[0]
            
            # Remove query parameters for consistency
            parsed = urlparse(absolute_url)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # Avoid duplicates
            if clean_url not in seen_links:
                seen_links.add(clean_url)
                links.append(clean_url)
        
        return links

