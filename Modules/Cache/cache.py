import json
import os
import logging
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime, timedelta

from codaio import Coda, Document, Cell, Row
from Modules.Commons import config, SummaryItem, TagInfo

logger = logging.getLogger(__name__)

class SummaryCache:
    """
    Cache for storing and retrieving summary items.
    Uses Coda as the primary backend with a local file cache.
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
        self.summary_id_dict = {}
        self.tag_info_dict = {}  # Dictionary to store tag information
        self.lock = asyncio.Lock()  # For thread-safe operations
        self.last_sync_time = None  # Track when the last sync occurred
        
         # Get sync interval from config
        cache_config = config.get_cache_config()
        sync_minutes = cache_config.sync_interval_minutes
        self.sync_interval = timedelta(minutes=sync_minutes)
        logger.info(f"Using sync interval of {sync_minutes} minutes")
        
        # Initialize Coda client
        target_config = config.get_target()
        if hasattr(target_config, "coda"):
            self.coda_config = target_config.coda
            self.coda_enabled = True
        else:
            self.coda_enabled = False
            logger.warning("Coda configuration not found, using local cache only")
        
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
                    self.summary_id_dict = {item.content_id: item for item in self.summaries}
                
                logger.info(f"Loaded {len(self.summaries)} summaries from local cache")
            else:
                logger.info(f"No cache file found at {self.cache_file}, starting with empty cache")
                self.summaries = []
                self.summary_id_dict = {}
        
        except Exception as e:
            logger.error(f"Error loading local cache: {e}")
            self.summaries = []
            self.summary_id_dict = {}
        
    
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
                
            logger.info(f"Saved {len(self.summaries)} summaries to local cache")
        except Exception as e:
            logger.error(f"Error saving local cache: {e}")
    
    async def _sync_with_coda(self, force_sync: bool = False) -> None:
        """
        Synchronize the local cache with Coda.
        
        Args:
            force_sync: If True, sync regardless of the time since last sync
        """
        if not self.coda_enabled:
            return
        
        # Check if sync is needed based on time elapsed
        current_time = datetime.now()
        if not force_sync and self.last_sync_time:
            time_since_last_sync = current_time - self.last_sync_time
            if time_since_last_sync < self.sync_interval:
                logger.debug(f"Skipping Coda sync - last sync was {time_since_last_sync.total_seconds()/60:.1f} minutes ago")
                return
            
        try:
            # Run in a thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            
            # Sync summaries
            coda_rows = await loop.run_in_executor(None, self._get_all_summary_coda_rows)
            
            # Sync tags
            tag_rows = await loop.run_in_executor(None, self._get_all_tag_rows)
            
            # Convert Coda rows to SummaryItems
            coda_summaries = []
            for row in coda_rows:
                try:
                    summary_item = self._coda_row_to_summary_item(row)
                    if summary_item:
                        coda_summaries.append(summary_item)
                except Exception as e:
                    logger.error(f"Error converting Coda row to SummaryItem: {e}")
            
            # Convert tag rows to TagInfo objects
            self.tag_info_dict = {}
            for row in tag_rows:
                try:
                    tag = row.get('Tag', '')
                    description = row.get('Description', '')
                    if tag:
                        self.tag_info_dict[tag] = TagInfo(tag, description)
                except Exception as e:
                    logger.error(f"Error converting Coda row to TagInfo: {e}")
            
            # Update local cache with Coda data
            # For each item in Coda, add it to local cache if not present
            
            for coda_item in coda_summaries:
                existing_item = self.summary_id_dict.get(coda_item.content_id)
                if existing_item is None:
                    self.summaries.append(coda_item)
                    self.summary_id_dict[coda_item.content_id] = coda_item
                    logger.debug(f"Added item from Coda to local cache: {coda_item.url}")
            
            # Save updated local cache
            await self._save_cache()
            
            # Update the last sync time
            self.last_sync_time = current_time
            
            logger.info(f"Synchronized local cache with Coda ({len(coda_summaries)} items, {len(self.tag_info_dict)} tags)")
        except Exception as e:
            logger.error(f"Error synchronizing with Coda: {e}")
    
    def _get_all_summary_coda_rows(self) -> List[Dict[str, Any]]:
        """Get all rows from Coda table."""
        if not self.coda_enabled:
            return []
            
        try:
            # Initialize Coda client
            coda = Coda(self.coda_config.api_key)
            # Get the doc and table
            doc = Document(self.coda_config.doc_id, coda=coda)
            table = doc.get_table(self.coda_config.table_id)
            
            # Get all rows
            rows = table.rows()
            
            # Convert rows to dictionaries
            result = []
            for row in rows:
                row_dict = {}
                for cell in row.cells():
                    row_dict[cell.column.name] = cell.value
                result.append(row_dict)
                
            return result
        except Exception as e:
            logger.error(f"Error getting rows from Coda: {e}")
            return []
    
    def _get_all_tag_rows(self) -> List[Dict[str, Any]]:
        """Get all rows from Coda tag table."""
        if not self.coda_enabled:
            return []
            
        try:
            # Initialize Coda client
            coda = Coda(self.coda_config.api_key)
            # Get the doc and table
            doc = Document(self.coda_config.doc_id, coda=coda)
            table = doc.get_table(self.coda_config.tag_table_id)
            
            # Get all rows
            rows = table.rows()
            
            # Convert rows to dictionaries
            result = []
            for row in rows:
                row_dict = {}
                for cell in row.cells():
                    row_dict[cell.column.name] = cell.value
                result.append(row_dict)
                
            return result
        except Exception as e:
            logger.error(f"Error getting rows from Coda tag table: {e}")
            return []
    

    def _add_or_update_coda_row(self, summary_item: SummaryItem) -> bool:
        """Add or update a row in Coda."""
        if not self.coda_enabled:
            return False
            
        try:
            # Initialize Coda client
            coda = Coda(self.coda_config.api_key)
            # Get the doc and table
            doc = Document(self.coda_config.doc_id, coda=coda)
            table = doc.get_table(self.coda_config.table_id)
            
            # Prepare cells for the row
            cells = []
            cells.append(Cell(column='URL', value_storage=summary_item.url))
            cells.append(Cell(column='Discord', value_storage=summary_item.thread_url))
            cells.append(Cell(column='Type', value_storage=summary_item.type))
            cells.append(Cell(column='ID', value_storage=summary_item.content_id))
            cells.append(Cell(column='Auteur', value_storage=summary_item.author))
            cells.append(Cell(column='Titre', value_storage=summary_item.title))
            cells.append(Cell(column='Résumé', value_storage=summary_item.summary))
            
            # Add tags if available
            if hasattr(summary_item, 'tags') and summary_item.tags:
                cells.append(Cell(column='Tags', value_storage=", ".join(summary_item.tags)))
            
            # Upsert the row to the table
            result = table.upsert_row(cells)
            
            return True
        except Exception as e:
            logger.error(f"Error adding/updating row in Coda: {e}")
            return False
    
    def _coda_row_to_summary_item(self, row: Dict[str, Any]) -> Optional[SummaryItem]:
        """Convert a Coda row to a SummaryItem."""
        try:
            # Extract tags as a list if present
            tags = []
            if 'Tags' in row and row['Tags']:
                tags = [tag.strip() for tag in row['Tags'].split(',')]
                
            return SummaryItem(
                type=row.get('Type', ''),
                content_id=row.get('ID', ''),
                title=row.get('Titre', ''),
                author=row.get('Auteur', ''),
                url=row.get('URL', ''),
                summary=row.get('Résumé', ''),
                content='',  # Content is not stored in Coda
                tags=tags,
                thread_url=row.get('Discord', '')
            )
        except Exception as e:
            logger.error(f"Error converting Coda row to SummaryItem: {e}")
            return None
    
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
        Add a summary item to the cache and Coda.
        
        Args:
            summary_item: The SummaryItem to add
        """
        async with self.lock:
            # Check if URL already exists in cache
            existing = self.summary_id_dict.get(summary_item.content_id)
            
            if existing:
                # Update existing item
                logger.info(f"Updating existing summary for content_id: {summary_item.content_id}")
                self.summaries.remove(existing)
                self.summaries.append(summary_item)
            else:
                # Add new item
                logger.info(f"Adding new summary for content_id: {summary_item.content_id}")
                self.summaries.append(summary_item)

            self.summary_id_dict[summary_item.content_id] = summary_item
            # Save cache to file
            await self._save_cache()
            
            # Add to Coda
            if self.coda_enabled:
                try:
                    # Run in a thread pool to avoid blocking the event loop
                    loop = asyncio.get_event_loop()
                    success = await loop.run_in_executor(None, lambda: self._add_or_update_coda_row(summary_item))
                    
                    if success:
                        logger.info(f"Added/updated summary in Coda for URL: {summary_item.url}")
                    else:
                        logger.warning(f"Failed to add/update summary in Coda for URL: {summary_item.url}")
                except Exception as e:
                    logger.error(f"Error adding summary to Coda: {e}")
    
    async def find_by_content_id(self, content_id: str) -> Optional[SummaryItem]:
        """
        Find a summary item by content ID.
        
        Args:
            content_id: The content ID to search for
            
        Returns:
            The matching SummaryItem, or None if not found
        """
        # First sync with Coda to ensure we have the latest data
        if self.coda_enabled:
            await self._sync_with_coda()
        
        # Search in local summaries
        for item in self.summaries:
            if item.content_id == content_id:
                return item
                
        return None

    async def find_by_tags(self, tags: List[str]) -> List[SummaryItem]:
        """
        Find summary items that match any of the given tags.
        
        Args:
            tags: List of tags to search for
            
        Returns:
            List of matching SummaryItems
        """
        # First sync with Coda to ensure we have the latest data
        if self.coda_enabled:
            await self._sync_with_coda()
        
        # Search in local summaries
        results = []
        for item in self.summaries:
            if any(tag.lower() in [t.lower() for t in item.tags] for tag in tags):
                results.append(item)
        return results
    
    async def get_all_summaries(self) -> List[SummaryItem]:
        """
        Get all summary items, syncing with Coda first.
        
        Returns:
            List of all SummaryItems
        """
        # Sync with Coda to ensure we have the latest data
        if self.coda_enabled:
            await self._sync_with_coda()
        
        return self.summaries.copy()
    
    async def get_tag_info(self) -> Dict[str, TagInfo]:
        """
        Get all tag information from Coda.
        
        Returns:
            Dictionary mapping tag names to TagInfo objects
        """
        # Sync with Coda to ensure we have the latest data
        if self.coda_enabled:
            await self._sync_with_coda()
        
        return self.tag_info_dict.copy()
    
    
def create_cache() -> SummaryCache:
    """
    Create and initialize the summary cache.
    
    Returns:
        A configured SummaryCache instance
    """
    return SummaryCache()