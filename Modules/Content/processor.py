import logging
from typing import Dict, Any, Callable, Awaitable, Optional, Tuple
import re
from urllib.parse import urlparse
from Modules.Commons import config, ContentItem
from . import youtube

logger = logging.getLogger(__name__)

# Type definition for content processor functions
ContentProcessorFunc = Callable[[str], Awaitable[Optional[ContentItem]]]

class ContentProcessor:
    """
    Content processor for fetching and processing content from URLs.
    Supports multiple domains through registered processor functions.
    """
    
    def __init__(self):
        """Initialize the content processor with empty processor registry."""
        self._processors: Dict[str, ContentProcessorFunc] = {}
        self._id_extractors: Dict[str, Callable[[str], Optional[str]]] = {}
        self._register_default_processors()
        
    def _register_default_processors(self):
        """Register the default content processors."""
        # Register YouTube processor
        self.register_processor("youtube.com", youtube.process_youtube)
        self.register_processor("youtu.be", youtube.process_youtube)
        
        # Register ID extractors
        self.register_id_extractor("youtube.com", youtube.extract_video_id)
        self.register_id_extractor("youtu.be", youtube.extract_video_id)
        
    def register_processor(self, domain: str, processor: ContentProcessorFunc) -> None:
        """
        Register a processor function for a specific domain.
        
        Args:
            domain: The domain name (e.g., 'youtube.com')
            processor: The async function that processes URLs from this domain
        """
        self._processors[domain] = processor
        logger.info(f"Registered content processor for domain: {domain}")
        
    def register_id_extractor(self, domain: str, extractor: Callable[[str], Optional[str]]) -> None:
        """
        Register an ID extractor function for a specific domain.
        
        Args:
            domain: The domain name (e.g., 'youtube.com')
            extractor: A function that extracts the platform-specific ID from a URL
        """
        self._id_extractors[domain] = extractor
        logger.info(f"Registered ID extractor for domain: {domain}")
        
    async def extract_content_id(self, url: str) -> Optional[str]:
        """
        Extract a standardized content ID from a URL.
        
        Args:
            url: The URL to process
            
        Returns:
            A standardized content ID (e.g., 'youtube:dQw4w9WgXcQ') or None if not supported
        """
        # Parse the URL to get the domain
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            return None
            
        # Find a matching domain and extractor
        extractor = None
        
        for domain, extract_func in self._id_extractors.items():
            if domain in parsed_url.netloc:
                extractor = extract_func
                break
                
        if not extractor:
            return None
            
        # Extract the ID
        id = extractor(url)
        if not id:
            return None
          
        return id
        
    async def process(self, url: str) -> Optional[ContentItem]:
        """
        Process a URL by finding and using the appropriate domain processor.
        
        Args:
            url: The URL to process
            
        Returns:
            A ContentItem object containing standardized content information
            
        Raises:
            ValueError: If the URL is invalid
            RuntimeError: If processing fails
        """
        # Parse the URL to get the domain
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            raise ValueError(f"Invalid URL: {url}")
            
        # Find a matching processor
        processor = None
        domain = None
        
        for d, proc_func in self._processors.items():
            if d in parsed_url.netloc:
                processor = proc_func
                domain = d
                break
                
        if not processor:
            raise RuntimeError(f"No processor registered for domain: {parsed_url.netloc}")
            
        try:
            # Process the URL
            logger.info(f"Processing URL: {url} with domain: {domain}")
            content = await processor(url)
            
            if not content:
                logger.warning(f"No content returned for URL: {url}")
                return None
                
            # Ensure URL is set in the content
            content.url = url
            
            # Extract and set content ID if not already set
            if 'content_id' not in content.metadata:
                content_id = await self.extract_content_id(url)
                if content_id:
                    content.metadata['content_id'] = content_id
                
            return content
            
        except Exception as e:
            logger.exception(f"Error processing URL {url}: {e}")
            raise RuntimeError(f"Failed to process URL: {str(e)}")

def create_content_processor() -> ContentProcessor:
    """
    Create and configure a new instance of the ContentProcessor.
    
    Returns:
        A configured ContentProcessor instance
    """
    return ContentProcessor()