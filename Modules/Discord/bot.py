import logging
import re

from typing import List, Optional, Callable, Any, Awaitable, Dict
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

            intents=intents,
            help_command=commands.DefaultHelpCommand(
                no_category="PIA Commands"
            )
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

        
        # Register commands
        @self.command(name="ping", help="Check if the bot is responsive")
        async def ping(ctx):
            """Simple command to check if the bot is responsive."""
            await ctx.send("Pong! I'm here and listening.")
            
        @self.command(name="channels", help="List monitored channels")
        async def channels(ctx):
            """List the channels being monitored by the bot."""
            channel_list = []
            for channel_id in self.monitored_channel_ids:
                channel = self.get_channel(channel_id)
                if channel:
                    channel_list.append(f"- {channel.name} (ID: {channel.id})")
                else:
                    channel_list.append(f"- Unknown channel (ID: {channel_id})")
            
            if channel_list:
                await ctx.send("I'm monitoring these channels:\n" + "\n".join(channel_list))
            else:
                await ctx.send("I'm not monitoring any channels.")
        
        logger.info("Commands registered successfully")
        
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
        
        # Verify that monitored channels exist and are accessible
        for channel_id in self.monitored_channel_ids:
            channel = self.get_channel(channel_id)
            if channel:
                logger.info(f"Monitoring channel: {channel.name} (ID: {channel_id})")
            else:
                logger.warning(f"Could not find channel with ID: {channel_id}")
        
        # Set custom status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for links to summarize"
            )
        )
        
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
            if await self._is_supported_url(url):
                logger.info(f"Processing URL: {url} from message {message.id}")
                await self._process_url(url, message)
    
    async def on_command_error(self, ctx, error):
        """
        Called when a command raises an error.
        
        Args:
            ctx: The command context
            error: The error that was raised
        """
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"Command not found. Use `{self.command_prefix}help` to see available commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
        else:
            logger.exception(f"Command error: {error}")
            await ctx.send(f"An error occurred: {str(error)}")
    
    async def _extract_urls(self, content: str) -> List[str]:
        """
        Extract URLs from message content.
        
        Args:
            content: The message content
            
        Returns:
            A list of extracted URLs
        """
        # URL extraction regex
        url_pattern = r'https?:\/\/\S+'
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
        # Extract domain for better thread naming
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        domain = domain_match.group(1) if domain_match else "link"
        
        # Limit thread name length
        max_name_length = 100  # Discord's limit
        thread_name = f"Discussion: {domain} - {url[:max_name_length-15]}"
        if len(thread_name) > max_name_length:
            thread_name = thread_name[:max_name_length-3] + "..."
        
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
                await thread.send("Error: Content processor not configured")
                return
                
            await thread.send(strings.CONTENT_YOUTUBE_FETCHING)
            content_item = await self._content_processor(url)
            
            if not content_item:
                await thread.send(f"Could not fetch content from {url}")
                return
                
            await thread.send(strings.DISCORD_CONTENT_FETCHED.format(type=content_item.type))
            
            # Summarize content
            if not self._summarizer:
                logger.error("Summarizer not set")
                await thread.send("Error: Summarizer not configured")
                return
                
            await thread.send(strings.SUMMARIZATION_PROCESSING)
            summary = await self._summarizer(content_item)
            
            if not summary:
                await thread.send("Could not generate summary")
                return
                
            await thread.send(strings.SUMMARIZATION_COMPLETE)
            
            # Send to targets
            if not self._target_handler:
                logger.error("Target handler not set")
                await thread.send("Error: Target handler not configured")
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
    except discord.LoginFailure:
        logging.error("Invalid Discord token. Please check your configuration.")
        raise
    except Exception as e:
        logging.error(f"Failed to start Discord bot: {e}")
        raise