import aiohttp
import asyncio
import logging
from typing import Set, Dict, Optional, List
from datetime import datetime
from urllib.parse import urljoin, urlparse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.utils import extract_doc_id, normalize_url, is_valid_help_url
from app.crawler.parser import HTMLParser
from app.database.models import CrawlerState

logger = logging.getLogger(__name__)


class Crawler:
    """Recursive crawler for ELMA365 documentation."""
    
    def __init__(self, db_session: Optional[AsyncSession] = None, max_pages: Optional[int] = None, platform_only: bool = False):
        self.base_url = settings.CRAWL_BASE_URL
        self.max_depth = settings.CRAWL_MAX_DEPTH
        self.delay = settings.CRAWL_DELAY
        self.max_concurrent = settings.CRAWL_MAX_CONCURRENT
        self.max_pages = max_pages  # Limit total number of pages to crawl
        self.platform_only = platform_only  # Only crawl /ru/help/platform/ URLs
        self.parser = HTMLParser(self.base_url)
        self.db_session = db_session
        
        # Crawling state
        self.visited_urls: Set[str] = set()
        self.queue: List[tuple[str, int]] = []  # (url, depth)
        self.semaphore: Optional[asyncio.Semaphore] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_crawling = False
        self.stats = {
            'total_crawled': 0,
            'total_failed': 0,
            'start_time': None,
            'end_time': None
        }
        self.crawler_state_id: Optional[int] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; ELMA365-Crawler/1.0)'
            }
        )
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def crawl_recursive(self, start_url: Optional[str] = None, on_doc_crawled: Optional[callable] = None) -> List[Dict]:
        """
        Start recursive crawling from /help/ root or specified URL.
        Returns list of crawled documents.
        
        Args:
            start_url: Starting URL for crawling
            on_doc_crawled: Optional async callback function(doc_data) called for each crawled document.
                          Use this to save documents immediately instead of storing in memory.
                          Signature: async def callback(doc_data: Dict) -> None
        """
        if self.is_crawling:
            logger.warning("Crawler is already running")
            return []
        
        self.is_crawling = True
        self.stats['start_time'] = datetime.now()
        self.visited_urls.clear()
        self.queue.clear()
        
        # Update state in DB
        await self._update_state("running", pages_total=0, pages_processed=0)
        
        # Determine start URL
        if start_url is None:
            # Try Russian help first (most common), fallback to /help/
            start_url = urljoin(self.base_url, '/ru/help/')
        else:
            start_url = normalize_url(start_url, self.base_url)
        
        # Initialize queue - always add start URL, even if it's a directory
        # We'll discover pages from it
        if start_url not in self.visited_urls:
            self.queue.append((start_url, 0))
        
        crawled_docs = []
        
        try:
            while self.queue:
                # Check if we've reached max_pages limit
                if self.max_pages and len(self.visited_urls) >= self.max_pages:
                    logger.info(f"Reached max_pages limit ({self.max_pages}), stopping crawl")
                    break
                
                # Get batch of URLs to crawl
                batch = []
                while self.queue and len(batch) < self.max_concurrent:
                    url, depth = self.queue.pop(0)
                    if url not in self.visited_urls and depth <= self.max_depth:
                        # Check max_pages limit before adding to batch
                        if self.max_pages and len(self.visited_urls) >= self.max_pages:
                            break
                        batch.append((url, depth))
                
                if not batch:
                    break
                
                # Crawl batch concurrently
                tasks = [self._crawl_url(url, depth) for url, depth in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Error crawling: {result}")
                        self.stats['total_failed'] += 1
                    elif result:
                        # Call callback immediately if provided (saves to DB right away)
                        if on_doc_crawled:
                            try:
                                await on_doc_crawled(result)
                            except Exception as e:
                                logger.error(f"Error in on_doc_crawled callback: {e}")
                        
                        # Still append to list for return value
                        # If using callback, only keep minimal data in memory to save RAM
                        if on_doc_crawled is None:
                            crawled_docs.append(result)
                        else:
                            # Keep only minimal metadata in memory when using callback
                            crawled_docs.append({
                                'doc_id': result.get('doc_id'),
                                'url': result.get('url'),
                                'title': result.get('title')
                            })
                        
                        # Discover new URLs from this page
                        if result.get('links'):
                            await self._discover_urls(result['links'], result.get('depth', 0) + 1)
                
                # Update state in DB
                await self._update_state(
                    "running",
                    pages_total=len(self.visited_urls) + len(self.queue),
                    pages_processed=len(self.visited_urls)
                )
                
                # Rate limiting
                if self.delay > 0:
                    await asyncio.sleep(self.delay)
        
        finally:
            self.is_crawling = False
            self.stats['end_time'] = datetime.now()
            
            # Update final state
            await self._update_state(
                "idle",
                pages_total=len(self.visited_urls),
                pages_processed=len(self.visited_urls)
            )
        
        return crawled_docs
    
    async def crawl_url(self, url: str) -> Optional[Dict]:
        """Crawl a single URL."""
        url = normalize_url(url, self.base_url)
        if not is_valid_help_url(url, self.base_url, platform_only=self.platform_only):
            logger.warning(f"Invalid help URL: {url}")
            return None
        
        async with self:
            return await self._crawl_url(url, 0)
    
    async def _crawl_url(self, url: str, depth: int) -> Optional[Dict]:
        """Crawl a single URL (internal method)."""
        if url in self.visited_urls:
            return None
        
        async with self.semaphore:
            try:
                logger.info(f"Crawling: {url} (depth: {depth})")
                
                # Follow redirects automatically (aiohttp does this by default)
                # But we need to track the final URL after redirects
                async with self.session.get(url, allow_redirects=True) as response:
                    # Get final URL after redirects
                    final_url = str(response.url)
                    
                    # Normalize the final URL to fix any duplicate paths
                    final_url = normalize_url(final_url, self.base_url)
                    
                    # If URL was redirected, use the final URL
                    if final_url != url:
                        logger.info(f"Redirected: {url} -> {final_url}")
                        url = final_url
                        # Check if we already visited the final URL
                        if url in self.visited_urls:
                            return None
                    
                    if response.status != 200:
                        logger.warning(f"Failed to fetch {url}: status {response.status}")
                        self.stats['total_failed'] += 1
                        return None
                    
                    # Check content type
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'text/html' not in content_type:
                        logger.debug(f"Skipping non-HTML content: {url} ({content_type})")
                        self.visited_urls.add(url)  # Mark as visited to avoid retrying
                        return None
                    
                    html = await response.text()
                    parsed_data = self.parser.parse(html, url)
                    
                    # Only save if we have meaningful content
                    # Skip pages that are just directories/indices without content
                    has_content = (
                        parsed_data.get('title') or 
                        len(parsed_data.get('plain_text', '')) > 100 or
                        url.endswith('.html')
                    )
                    
                    doc_id = extract_doc_id(url)
                    
                    doc_data = {
                        'doc_id': doc_id,
                        'url': url,
                        'title': parsed_data['title'],
                        'breadcrumbs': parsed_data['breadcrumbs'],
                        'section': parsed_data['section'],
                        'html': parsed_data['html'],
                        'plain_text': parsed_data['plain_text'],
                        'last_crawled': datetime.now(),
                        'links': parsed_data['links'],
                        'depth': depth
                    }
                    
                    self.visited_urls.add(url)
                    self.stats['total_crawled'] += 1
                    
                    # Log discovered links
                    if parsed_data.get('links'):
                        logger.debug(f"Found {len(parsed_data['links'])} links on {url}")
                    
                    # Return doc_data even for directory pages (they might have links)
                    # The storage layer can decide whether to save based on content
                    return doc_data
            
            except Exception as e:
                logger.error(f"Error crawling {url}: {e}")
                self.stats['total_failed'] += 1
                return None
    
    async def _discover_urls(self, links: List[str], depth: int):
        """Discover and queue new URLs from links."""
        discovered_count = 0
        for link in links:
            normalized = normalize_url(link, self.base_url)
            if is_valid_help_url(normalized, self.base_url, platform_only=self.platform_only):
                if normalized not in self.visited_urls:
                    # Check max_pages limit
                    if self.max_pages and len(self.visited_urls) >= self.max_pages:
                        break
                    # Check if already in queue
                    if not any(url == normalized for url, _ in self.queue):
                        self.queue.append((normalized, depth))
                        discovered_count += 1
        
        if discovered_count > 0:
            logger.info(f"Discovered {discovered_count} new URLs at depth {depth}")
    
    def get_status(self) -> Dict:
        """Get current crawling status."""
        return {
            'is_crawling': self.is_crawling,
            'visited_count': len(self.visited_urls),
            'queue_size': len(self.queue),
            'stats': self.stats.copy()
        }
    
    def add_url(self, url: str):
        """Manually add URL to crawl queue."""
        url = normalize_url(url, self.base_url)
        if is_valid_help_url(url, self.base_url, platform_only=self.platform_only):
            if url not in self.visited_urls:
                if not any(u == url for u, _ in self.queue):
                    self.queue.append((url, 0))
                    logger.info(f"Added URL to queue: {url}")
        else:
            logger.warning(f"Invalid help URL: {url}")
    
    async def _update_state(
        self,
        status: str,
        pages_total: Optional[int] = None,
        pages_processed: Optional[int] = None
    ):
        """Update crawler state in database."""
        if not self.db_session:
            return
        
        try:
            # Get or create state
            if self.crawler_state_id:
                stmt = select(CrawlerState).where(CrawlerState.id == self.crawler_state_id)
                result = await self.db_session.execute(stmt)
                state = result.scalar_one_or_none()
            else:
                state = None
            
            if not state:
                state = CrawlerState(
                    status=status,
                    pages_total=pages_total or 0,
                    pages_processed=pages_processed or 0,
                    last_run=datetime.now()
                )
                self.db_session.add(state)
            else:
                state.status = status
                state.last_run = datetime.now()
                if pages_total is not None:
                    state.pages_total = pages_total
                if pages_processed is not None:
                    state.pages_processed = pages_processed
            
            await self.db_session.commit()
            await self.db_session.refresh(state)
            self.crawler_state_id = state.id
            
        except Exception as e:
            logger.error(f"Error updating crawler state: {e}", exc_info=True)
            await self.db_session.rollback()

