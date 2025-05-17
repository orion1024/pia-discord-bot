import logging
from typing import Dict, Any, Callable, Awaitable, Optional, List
import json

from Modules.Commons import config, sanitize_for_logging, SummaryItem, ContentItem, TagInfo

from .claude import summarize_with_claude
from .openai import summarize_with_chatgpt
   

logger = logging.getLogger(__name__)

# Type definition for summarizer functions
SummarizerFunc = Callable[[ContentItem, Optional[Dict[str, TagInfo]]], Awaitable[SummaryItem]]

class Summarizer:
    """
    Summarizer for generating summaries of content using various LLM providers.
    Supports multiple LLM providers through registered summarizer functions.
    """
    
    def __init__(self):
        """Initialize the summarizer with empty summarizer registry."""
        self._summarizers: Dict[str, SummarizerFunc] = {}
        
    def register_summarizer(self, provider: str, summarizer: SummarizerFunc) -> None:
        """
        Register a summarizer function for a specific LLM provider.
        
        Args:
            provider: The LLM provider name (e.g., 'claude')
            summarizer: The async function that summarizes content using this provider
        """
        self._summarizers[provider] = summarizer
        logger.info(f"Registered summarizer for provider: {provider}")
        
    async def summarize(self, content_item: ContentItem, tag_info: Optional[Dict[str, TagInfo]] = None) -> SummaryItem:
        """
        Summarize content using the configured LLM provider.
        
        Args:
            content_item: The ContentItem to summarize
            tag_info: Optional dictionary of TagInfo objects to help with tagging
            
        Returns:
            A SummaryItem containing the summary and metadata
            
        Raises:
            ValueError: If the content is invalid
            RuntimeError: If summarization fails
        """
        if not content_item:
            raise ValueError("Cannot summarize empty content")
            
        # Get the configured provider
        summarization_config = config.get_summarization()
        provider = summarization_config.provider
        
        # Find the appropriate summarizer
        summarizer = self._summarizers.get(provider)
        if not summarizer:
            raise RuntimeError(f"No summarizer registered for provider: {provider}")
            
        try:
            # Generate the summary
            logger.info(f"Generating summary using provider: {provider}")
            summary_item = await summarizer(content_item, tag_info)
            
            # Log a sanitized version of the summary for debugging
            logger.info(f"Generated tags: {sanitize_for_logging(summary_item.tags[:100])}...")
            logger.info(f"Generated summary: {sanitize_for_logging(summary_item.summary[:100])}...")
            
            return summary_item
        except Exception as e:
            logger.exception(f"Error generating summary: {e}")
            raise RuntimeError(f"Failed to generate summary: {str(e)}")

def create_summarizer() -> Summarizer:
    """
    Create and configure a summarizer with registered summarizers for supported LLM providers.
    
    Returns:
        A configured Summarizer instance
    """
    summarizer = Summarizer()
    
    # Register summarizers for supported providers
    summarizer.register_summarizer("claude", summarize_with_claude)
    
    # Import and register the ChatGPT summarizer
    summarizer.register_summarizer("chatgpt", summarize_with_chatgpt)
    
    return summarizer
