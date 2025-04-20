import json
import os
import logging
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime

from Modules.Commons import config, SummaryItem

logger = logging.getLogger(__name__)

class SummaryCache:
    """
    Cache for storing and retrieving summary items.
    Uses a local JSON file to maintain persistence between bot restarts.
    """
    
    def __init__(self, cache_file: str = None):
        """
        Initialize the summary cache.
        
        Args:
            cache_file: Path to the cache file (defaults to config value or 'summary_cache.json')
        """
        # Get cache file from config or use default
        self.cache_file = cache_file or config.get_cache_file() or "summary_cache.json"
        self.summaries = []
        self.lock = asyncio.Lock()  # For thread-safe operations
        
        # Load existing cache if available
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load summaries from the cache file if it exists."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Convert dictionary data back to SummaryItem objects
                    self.summaries = [self._dict_to_summary_item(item) for item in data]
                    
                logger.info(f"Loaded {len(self.summaries)} summaries from cache")
            else:
                logger.info(f"No cache file found at {self.cache_file}, starting with empty cache")
                self.summaries = []
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            self.summaries = []
    
    async def _save_cache(self) -> None:
        """Save summaries to the cache file."""
        try:
            # Convert SummaryItem objects to dictionaries
            data = [self._summary_item_to_dict(item) for item in self.summaries]
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.cache_file)), exist_ok=True)
            
            # Write to file
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved {len(self.summaries)} summaries to cache")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def _summary_item_to_dict(self, item: SummaryItem) -> Dict[str, Any]:
        """Convert a SummaryItem to a dictionary for JSON serialization."""
        return {
            "type": item.type,
            "content_id": item.content_id,
            "title": item.title,
            "author": item.author,
            "url": item.url,
            "summary": item.summary,
            "content": item.content,
            "tags": item.tags,
            "thread_url": item.thread_url,
            "timestamp": datetime.now().isoformat()  # Add timestamp for tracking
        }
    
    def _dict_to_summary_item(self, data: Dict[str, Any]) -> SummaryItem:
        """Convert a dictionary to a SummaryItem."""
        return SummaryItem(
            type=data.get("type", ""),
            content_id=data.get("content_id", ""),
            title=data.get("title", ""),
            author=data.get("author", ""),
            url=data.get("url", ""),
            summary=data.get("summary", ""),
            content=data.get("content", ""),
            tags=data.get("tags", []),
            thread_url=data.get("thread_url", "")
        )
    
    async def add_summary(self, summary_item: SummaryItem) -> None:
        """
        Add a summary item to the cache.
        
        Args:
            summary_item: The SummaryItem to add
        """
        async with self.lock:
            # Check if URL already exists in cache
            existing = self.find_by_url(summary_item.url)
            
            if existing:
                # Update existing item
                logger.info(f"Updating existing summary for URL: {summary_item.url}")
                self.summaries.remove(existing)
                self.summaries.append(summary_item)
            else:
                # Add new item
                logger.info(f"Adding new summary for URL: {summary_item.url}")
                self.summaries.append(summary_item)
            
            # Save cache to file
            await self._save_cache()
    
    def find_by_url(self, url: str) -> Optional[SummaryItem]:
        """
        Find a summary item by URL.
        
        Args:
            url: The URL to search for
            
        Returns:
            The matching SummaryItem, or None if not found
        """
        logger.debug(f"Finding summary by URL: {url}")
        
        for item in self.summaries:
            if item.url == url:
                return item
            
        logger.debug(f"No summary found for URL: {url}")

        return None
    
    def find_by_content_id(self, content_id: str) -> Optional[SummaryItem]:
        """
        Find a summary item by content ID.
        
        Args:
            content_id: The content ID to search for
            
        Returns:
            The matching SummaryItem, or None if not found
        """
        for item in self.summaries:
            if item.content_id == content_id:
                return item
            
        return None

    def find_by_tags(self, tags: List[str]) -> List[SummaryItem]:
        """
        Find summary items that match any of the given tags.
        
        Args:
            tags: List of tags to search for
            
        Returns:
            List of matching SummaryItems
        """
        results = []
        for item in self.summaries:
            if any(tag.lower() in [t.lower() for t in item.tags] for tag in tags):
                results.append(item)
        return results
    
    def get_all_summaries(self) -> List[SummaryItem]:
        """
        Get all summary items in the cache.
        
        Returns:
            List of all SummaryItems
        """
        return self.summaries.copy()
    
    async def update_thread_url(self, url: str, thread_url: str) -> None:
        """
        Update the thread URL for a summary item.
        
        Args:
            url: The content URL
            thread_url: The Discord thread URL
        """
        async with self.lock:
            item = self.find_by_url(url)
            if item:
                item.thread_url = thread_url
                await self._save_cache()
                logger.info(f"Updated thread URL for {url}")

def create_cache() -> SummaryCache:
    """
    Create and initialize the summary cache.
    
    Returns:
        A configured SummaryCache instance
    """
    return SummaryCache()