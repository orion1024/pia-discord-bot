import logging
import re
from typing import List, Optional, Callable, Any, Awaitable
import discord
from discord.ext import commands

from Modules.Commons import config
from Modules import strings

logger = logging.getLogger(__name__)

class PiaBot(commands.Bot):
    """
    Main Discord bot class for PIA.
    Handles connection to Discord and message processing.
    """
    
    def __init__(self):
        """Initialize the Discord bot with required intents and command prefix."""
        intents = discord.Intents.default()
        intents.message_content = True  # Required to read message content
        intents.messages = True
        
        discord_config = config.get_discord()
        super().__init__(
            command_prefix=discord_config.command_prefix,
            intents=intents
        )
        
        self.monitored_channel_ids = [int(channel_id) for channel_id in discord_config.monitored_channels]
        self._content_processor = None
        self._summarizer = None
        self._target_handler = None
        
    async def setup_hook(self) -> None:
        """
        Set up the bot's event handlers and commands.
        This is called automatically when the bot is started.
        """
        logger.info("Setting up PIA Discord bot...")
        # Register commands will be added here
        
    def set_content_processor(self, processor: Callable[[str], Awaitable[Any]]) -> None:
        """
        Set the content processor function.
        
        Args:
            processor: A function that processes content from a URL
        """
        self._content_processor = processor
        
    def set_summarizer(self, summarizer: Callable[[Any], Awaitable[str]]) -> None:
        """
        Set the summarizer function.
        
        Args:
            summarizer: A function that summarizes content
        """
        self._summarizer = summarizer
        
    def set_target_handler(self, handler: Callable[[str, str, discord.Thread], Awaitable[None]]) -> None:
        """
        Set the target handler function.
        
        Args:
            handler: A function that handles sending the summary to targets
        """
        self._target_handler = handler
        
    async def on_ready(self):
        """Called when the bot is ready and connected to Discord."""
        logger.info(f"Logged in as {self.user.name} ({self.user.id})")
        logger.info(f"Monitoring channels: {self.monitored_channel_ids}")
        
    async def on_message(self, message: discord.Message):
        """
        Called when a message is received.
        Checks if the message contains a supported URL and processes it.
        
        Args:
            message: The Discord message
        """
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
            
        # Process commands first
        await self.process_commands(message)
        
        # Check if the message is in a monitored channel
        if message.channel.id not in self.monitored_channel_ids:
            return
            
        # Check if the message contains a URL
        urls = await self._extract_urls(message.content)
        if not urls:
            return
            
        # Process each URL
        for url in urls:
            await self._process_url(url, message)
    
    async def _extract_urls(self, content: str) -> List[str]:
        """
        Extract URLs from message content.
        
        Args:
            content: The message content
            
        Returns:
            A list of extracted URLs
        """
        # Simple URL extraction regex - can be improved
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        return re.findall(url_pattern, content)
    
    async def _is_supported_url(self, url: str) -> bool:
        """
        Check if a URL is from a supported domain.
        
        Args:
            url: The URL to check
            
        Returns:
            True if the URL is supported, False otherwise
        """
        supported_domains = config.get_content().supported_domains
        return any(domain in url for domain in supported_domains)
    
    async def _check_duplicate(self, url: str) -> Optional[discord.Thread]:
        """
        Check if a URL has already been processed.
        
        Args:
            url: The URL to check
            
        Returns:
            The existing thread if the URL is a duplicate, None otherwise
        """
        # This will be implemented later with Coda integration
        # For now, return None (no duplicates)
        return None
    
    async def _create_thread(self, url: str, message: discord.Message) -> discord.Thread:
        """
        Create a new thread for a URL.
        
        Args:
            url: The URL
            message: The original message
            
        Returns:
            The created thread
        """
        # Create a thread name from the URL
        thread_name = f"Discussion: {url[:50]}"
        
        # Create the thread
        thread = await message.create_thread(name=thread_name)
        
        # Send initial message
        await thread.send(strings.DISCORD_THREAD_CREATED.format(url=url))
        
        return thread
    
    async def _process_url(self, url: str, message: discord.Message) -> None:
        """
        Process a URL from a message.
        
        Args:
            url: The URL to process
            message: The original message
        """
        # Check if the URL is supported
        if not await self._is_supported_url(url):
            return
            
        # Check for duplicates
        existing_thread = await self._check_duplicate(url)
        if existing_thread:
            # Notify about duplicate
            thread_url = f"https://discord.com/channels/{message.guild.id}/{existing_thread.id}"
            await message.channel.send(
                strings.DISCORD_DUPLICATE_DETECTED.format(thread_url=thread_url)
            )
            return
            
        # Create a thread for the URL
        thread = await self._create_thread(url, message)
        
        try:
            # Fetch content
            if not self._content_processor:
                logger.error("Content processor not set")
                return
                
            await thread.send(strings.CONTENT_YOUTUBE_FETCHING)
            content = await self._content_processor(url)
            await thread.send(strings.DISCORD_CONTENT_FETCHED.format(url=url))
            
            # Summarize content
            if not self._summarizer:
                logger.error("Summarizer not set")
                return
                
            await thread.send(strings.SUMMARIZATION_PROCESSING)
            summary = await self._summarizer(content)
            await thread.send(strings.SUMMARIZATION_COMPLETE)
            
            # Send to targets
            if not self._target_handler:
                logger.error("Target handler not set")
                return
                
            await self._target_handler(url, summary, thread)
            
        except Exception as e:
            logger.exception(f"Error processing URL {url}: {e}")
            await thread.send(strings.DISCORD_ERROR_FETCHING.format(url=url, error=str(e)))

def create_bot() -> PiaBot:
    """
    Create and configure a new instance of the PIA Discord bot.
    
    Returns:
        A configured PiaBot instance
    """
    return PiaBot()

async def start_bot(bot: PiaBot) -> None:
    """
    Start the Discord bot.
    
    Args:
        bot: The PiaBot instance to start
    """
    discord_config = config.get_discord()
    try:
        logging.info("Starting Discord bot...")
        await bot.start(discord_config.token)
    except Exception as e:
        logging.error(f"Failed to start Discord bot: {e}")
        raise