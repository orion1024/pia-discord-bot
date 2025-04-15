import logging
from typing import Dict, Any, Callable, Awaitable, Optional
import re
from urllib.parse import urlparse

from Modules.Commons import config

logger = logging.getLogger(__name__)

# Type definition for content processor functions
ContentProcessorFunc = Callable[[str], Awaitable[Dict[str, Any]]]

class ContentProcessor:
    """
    Content processor for fetching and processing content from URLs.
    Supports multiple content sources through registered processor functions.
    """
    
    def __init__(self):
        """Initialize the content processor with empty processor registry."""
        self._processors: Dict[str, ContentProcessorFunc] = {}
        
    def register_processor(self, domain: str, processor: ContentProcessorFunc) -> None:
        """
        Register a processor function for a specific domain.
        
        Args:
            domain: The domain this processor handles (e.g., 'youtube.com')
            processor: The async function that processes URLs from this domain
        """
        self._processors[domain] = processor
        logger.info(f"Registered content processor for domain: {domain}")
        
    async def process(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Process a URL by finding and using the appropriate domain processor.
        
        Args:
            url: The URL to process
            
        Returns:
            A dictionary containing the processed content, or None if no processor is found
            
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
        for domain, proc_func in self._processors.items():
            if domain in parsed_url.netloc:
                processor = proc_func
                break
                
        if not processor:
            logger.warning(f"No content processor found for URL: {url}")
            return None
            
        try:
            # Process the content
            logger.info(f"Processing content from URL: {url}")
            content = await processor(url)
            return content
        except Exception as e:
            logger.exception(f"Error processing content from URL {url}: {e}")
            raise RuntimeError(f"Failed to process content: {str(e)}")

# YouTube content processor (placeholder)
async def process_youtube_content(url: str) -> Dict[str, Any]:
    """
    Process content from a YouTube URL.
    
    Args:
        url: The YouTube URL to process
        
    Returns:
        A dictionary containing the processed YouTube content
        
    Raises:
        RuntimeError: If processing fails
    """
    # This is a placeholder - actual implementation will come later
    logger.info(f"Processing YouTube content from URL: {url}")
    
    # Extract video ID from URL (simplified)
    video_id = None
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            break
    
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")
    
    # Placeholder for actual YouTube API call
    return {
        "type": "youtube",
        "video_id": video_id,
        "title": "Sample YouTube Video",
        "description": "This is a placeholder description",
        "channel": "Sample Channel",
        "duration": "10:00",
        "publish_date": "2023-01-01",
        "url": url
    }

def create_content_processor() -> ContentProcessor:
    """
    Create and configure a content processor with registered processors for supported domains.
    
    Returns:
        A configured ContentProcessor instance
    """
    processor = ContentProcessor()
    
    # Register processors for supported domains
    processor.register_processor("youtube.com", process_youtube_content)
    processor.register_processor("youtu.be", process_youtube_content)
    
    return processor
