import os, json, datetime, re, logging

from typing import List, Optional, Callable, Any, Awaitable, Dict
import discord
from discord.ext import commands

from Modules.Commons import config, SummaryItem
from Modules import strings

logger = logging.getLogger(__name__)

class PiaBot(commands.Bot):
    """
    Main Discord bot class for PIA.
    Handles connection to Discord and message processing.
    """
    
    THREAD_NAME_LIMIT = 100

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

    async def close(self):
        if self.is_closed():
            return
        await self.http.close()
        
        await super().close()

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
            if not (isinstance(ctx.channel, discord.DMChannel) or ctx.channel.id in self.monitored_channel_ids):
                return
            
            await ctx.message.reply("Pong! I'm here and listening.")
            
        @self.command(name="channels", help="List monitored channels [PM only]")
        async def channels(ctx):
            """List the channels being monitored by the bot."""
            if not isinstance(ctx.channel, discord.DMChannel):
                await ctx.message.reply("Cette commande peut être utilisée uniquement dans un message privé au bot.")
                return
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
        
        @self.command(name="scan", help="Scan channel messages for links (days_back: int) [Admin only]")
        async def scan(ctx, days_back: int):
            """Scan channel messages for the specified number of days back."""
            if not (ctx.channel.id in self.monitored_channel_ids):
                return
            
            if not await self._check_moderator_permissions(ctx):
                await ctx.message.reply("You don't have permission to use this command.")
                return
            
            if days_back <= 0:
                await ctx.message.reply("Please provide a positive number of days to scan.")
                return
            
            await ctx.message.reply(f"Starting to scan messages from the last {days_back} days in this channel...")
        
            # Call the placeholder method that will handle the scanning logic
            scan_results = await self._scan_channel_messages(ctx.channel, days_back)
        
            # Reply with results
            await ctx.message.reply(f"Scan complete! Messages scanned: {scan_results['scanned']}, "
                          f"Already processed: {scan_results['processed']}, "
                          f"Not yet processed: {scan_results['not_processed']}")
        
        @self.command(name="queue", help="Display information about unprocessed URLs [PM only, Admin only]")
        async def queue(ctx):
            """Display information about unprocessed URLs from the local file."""
            if not isinstance(ctx.channel, discord.DMChannel):
                await ctx.message.reply("Cette commande peut être utilisée uniquement dans un message privé au bot.")
                return
            
            if not await self._check_moderator_permissions(ctx):
                await ctx.message.reply("You don't have permission to use this command.")
                return
            
            try:
                # Check if the unprocessed URLs file exists
                filename = "data/unprocessed_urls.json"
                if not os.path.exists(filename):
                    await ctx.send("No unprocessed URLs found.")
                    return
            
                # Load unprocessed URLs from file
                with open(filename, 'r', encoding='utf-8') as f:
                    unprocessed_urls = json.load(f)
            
                if not unprocessed_urls:
                    await ctx.send("No unprocessed URLs in queue.")
                    return
            
                # Count total unprocessed URLs
                total_urls = len(unprocessed_urls)
        
                # Count URLs in existing threads
                urls_in_threads = sum(1 for url in unprocessed_urls if url.get("thread_id"))
        
                # Group by content type (extracted from content_id)
                content_types = {}
                for url in unprocessed_urls:
                    content_id = url.get("content_id", "")
                    # Content ID format is typically "type/id", e.g., "youtube/abc123"
                    content_type = content_id.split("/")[0] if "/" in content_id else "unknown"
                    content_types[content_type] = content_types.get(content_type, 0) + 1
            
                # Create a formatted message
                message = f"**Unprocessed URLs Queue**\n\n"
                message += f"Total unprocessed URLs: **{total_urls}**\n"
                message += f"URLs in existing threads: **{urls_in_threads}**\n"
                message += f"URLs without threads: **{total_urls - urls_in_threads}**\n\n"
        
                # Add breakdown by content type
                message += "**Breakdown by content type:**\n"
                for content_type, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / total_urls) * 100
                    message += f"- {content_type}: **{count}** ({percentage:.1f}%)\n"
            
                await ctx.send(message)
        
            except Exception as e:
                logger.exception(f"Error displaying queue: {e}")
                await ctx.send(f"An error occurred while retrieving the queue: {str(e)}")
        
        @self.command(name="process", help="Process unprocessed URLs from the queue [Private message only, Permission needed]")
        async def process_queue(ctx, limit: int = 5):
            """
            Process unprocessed URLs from the queue.
            
            Args:
                limit: Maximum number of URLs to process (default: 5)
            """
            if not isinstance(ctx.channel, discord.DMChannel):
                await ctx.message.reply("Cette commande peut être utilisée uniquement dans un message privé au bot.")
                return
            
            if not await self._check_moderator_permissions(ctx):
                await ctx.message.reply("You don't have permission to use this command.")
                return
            
            try:
                # Check if the unprocessed URLs file exists
                filename = "data/unprocessed_urls.json"
                if not os.path.exists(filename):
                    await ctx.send("No unprocessed URLs found.")
                    return
                
                # Load unprocessed URLs from file
                with open(filename, 'r', encoding='utf-8') as f:
                    unprocessed_urls = json.load(f)
                
                if not unprocessed_urls:
                    await ctx.send("No unprocessed URLs in queue.")
                    return
                
                # Limit the number of URLs to process
                urls_to_process = unprocessed_urls[:limit]
            
                # Send an initial feedback message that we'll update
                feedback_content = "Starting to process URLs from the queue...\n\n"
                feedback_message = await ctx.send(feedback_content, suppress_embeds=True)
                
                # Process each URL
                processed_indices = []
                success_count = 0
                error_count = 0
            
                for i, url_data in enumerate(urls_to_process):
                    url = url_data.get("url")
                    if not url:
                        continue
                    
                    try:
                        # Get the original message if possible
                        message = None
                        channel_id = url_data.get("channel_id")
                        message_id = url_data.get("message_id")
                    
                        if channel_id and message_id:
                            try:
                                channel = self.get_channel(int(channel_id))
                                if channel:
                                    message = await channel.fetch_message(int(message_id))
                            except Exception as e:
                                logger.warning(f"Could not fetch original message: {e}")
                                continue
                    
                        # Process the URL
                        new_content += f"Processing URL {i+1}/{len(urls_to_process)}: {url}\n"
                        # TODO : check limit on message length (2000 chars)
                        if (len(new_content) + len(feedback_content)) < 2000:
                            feedback_content += new_content
                            await feedback_message.edit(content=feedback_content, suppress=True)
                        else:
                            # If we exceed the limit, start a new message
                            feedback_content = new_content
                            feedback_message = await ctx.send(feedback_content, suppress_embeds=True)
                            
                        
                        summary = await self._process_url(url, message)

                        # Mark as processed
                        processed_indices.append(i)
                        success_count += 1
                        
                        if summary:
                            new_content += f"✅ Successfully processed content: {summary.title}\n"
                        else:
                            # If _process_url returns None, it means the content has already been processed
                            new_content += f"✅ Already processed, skipped it.\n"
                        
                        if (len(new_content) + len(feedback_content)) < 2000:
                            feedback_content += new_content
                            await feedback_message.edit(content=feedback_content, suppress=True)
                        else:
                            # If we exceed the limit, start a new message
                            feedback_content = new_content
                            feedback_message = await ctx.send(feedback_content, suppress_embeds=True)
                    
                    except Exception as e:
                        logger.exception(f"Error processing URL {url}: {e}")
                        new_content += f"❌ Error processing URL {url}: {str(e)}\n"
                        if (len(new_content) + len(feedback_content)) < 2000:
                            feedback_content += new_content
                            await feedback_message.edit(content=feedback_content, suppress=True)
                        else:
                            # If we exceed the limit, start a new message
                            feedback_content = new_content
                            feedback_message = await ctx.send(feedback_content, suppress_embeds=True)
                        error_count += 1
            
                # Remove processed URLs from the file
                if processed_indices:
                    # Remove in reverse order to avoid index issues
                    for i in sorted(processed_indices, reverse=True):
                        if i < len(unprocessed_urls):
                            unprocessed_urls.pop(i)
                
                    # Save updated list back to file
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(unprocessed_urls, f, indent=2)
            
                # Send summary
                feedback_content += f"\nProcessing complete. Successfully processed: {success_count}, Errors: {error_count}, Remaining in queue: {len(unprocessed_urls)}"
                await feedback_message.edit(content=feedback_content, suppress=True)
            
            except Exception as e:
                logger.exception(f"Error processing queue: {e}")
                await ctx.send(f"An error occurred while processing the queue: {str(e)}")
                
        @self.command(name="search", help="Search for summaries by tag (search_term: str) [Private message only]")
        async def search_by_tag(ctx, *, search_term: str):
            """
            Search for summaries that have tags matching the given search term.
            
            Args:
                search_term: The term to search for in tags
            """
            if not isinstance(ctx.channel, discord.DMChannel):
                await ctx.message.reply("Cette commande peut être utilisée uniquement dans un message privé au bot.")
                return
            
            if not hasattr(self, '_summary_retriever'):
                await ctx.send("Error: Summary retriever not configured")
                return
            await ctx.send(f"Recherche de threads avec des tags contenant `{search_term}`...")
            try:
                # Get all summaries
                all_summaries = await self._summary_retriever()
            
                if not all_summaries:
                    await ctx.send("Aucun thread trouvé.")
                    return
                
                # Filter summaries by tag match (case-insensitive)
                search_term = search_term.lower()
                matching_summaries = []
            
                for summary in all_summaries:
                    # Check if any tag contains the search term
                    if any(search_term in tag.lower() for tag in summary.tags):
                        matching_summaries.append(summary)
            
                if not matching_summaries:
                    await ctx.send(f"Aucun thread ne correspond à '{search_term}'.")
                    return
                
                # Format results
                result_lines = []
                for i, summary in enumerate(matching_summaries, 1):
                    # Extract thread ID from thread URL
                    # thread_id = summary.thread_url.split('/')[-1] if summary.thread_url else "Unknown"
                    # thread_link = f"<https://discord.com/channels/{ctx.guild.id}/{thread_id}>"
                
                    # Format matching tags
                    matching_tags = [f"`{tag}`" for tag in summary.tags if search_term in tag.lower()]
                    tags_str = ", ".join(matching_tags)
                
                    # Create result line with title and link
                    result_lines.append(f"{i}. **[{summary.title}]({summary.thread_url})** - Tags: {tags_str}")
            
                # Create response message
                response = f"**{len(matching_summaries)} thread(s) trouvé(s) :**\n\n"
                response += "\n".join(result_lines)
            
                # Send response
                await ctx.send(response)
        
            except Exception as e:
                logger.exception(f"Error searching summaries by tag: {e}")
                await ctx.send(f"Erreur pendant la recherche: {str(e)}")

        logger.info("Commands registered successfully")
    
    def set_content_id_extractor(self, extractor: Callable[[str], Awaitable[Optional[str]]]) -> None:
        """
        Set the content ID extractor function.
        
        Args:
            extractor: A function that extracts a content ID from a URL
        """
        self._content_id_extractor = extractor
        
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
        
    def set_target_handler(self, handler: Callable[[str, str, discord.Thread, SummaryItem], Awaitable[None]]) -> None:
        """
        Set the target handler function.
        
        Args:
            handler: A function that handles sending the summary to targets
        """
        self._target_handler = handler
        
    def set_duplicate_checker(self, checker: Callable[[str], Awaitable[Optional[SummaryItem]]]) -> None:
        """
        Set the duplicate checker function.
        
        Args:
            checker: A function that checks if a URL has already been processed
        """
        self._duplicate_checker = checker
        
    def set_thread_url_updater(self, updater: Callable[[str, str], Awaitable[None]]) -> None:
        """
        Set the thread URL updater function.
        
        Args:
            updater: A function that updates the thread URL for a URL
        """
        self._thread_url_updater = updater

    def set_summary_retriever(self, retriever: Callable[[], Awaitable[List[SummaryItem]]]) -> None:
        """
        Set the summary retriever function.
        
        Args:
            retriever: A function that retrieves all summary items from the cache
        """
        self._summary_retriever = retriever

    async def _check_duplicate(self, url: str) -> Optional[discord.Thread]:
        """
        Check if a URL has already been processed.
        
        Args:
            url: The URL to check
            
        Returns:
            The existing thread if the URL is a duplicate, None otherwise
        """
        # Use the duplicate checker if available
        if hasattr(self, '_duplicate_checker'):
            logger.info("Checking for duplicates...")
            existing_summary = await self._duplicate_checker(url)
            if existing_summary and existing_summary.thread_url:
                # Get the thread ID from the thread URL
                # Thread URLs are in the format: https://discord.com/channels/{guild_id}/{channel_id}/{thread_id}
                try:
                    thread_id = int(existing_summary.thread_url.split('/')[-1])
                    thread = self.get_channel(thread_id)
                    if thread:
                        return thread
                except (ValueError, IndexError):
                    logger.warning(f"Invalid thread URL in cache: {existing_summary.thread_url}")
        
        # No duplicate found or thread not accessible
        return None

    def _generate_default_thread_name(self, url: str) -> str:
        """
        Create a thread name from a URL.

        Args:
            url: The URL to create a thread name from
    
        Returns:
            A formatted thread name
        """
        # Extract domain for better thread naming
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        domain = domain_match.group(1) if domain_match else "link"

        # Limit thread name length
        max_length = self.THREAD_NAME_LIMIT
        thread_name = f"Discussion: {domain} - {url[:max_length-15]}"
        if len(thread_name) > max_length:
            thread_name = thread_name[:max_length-3] + "..."
    
        return thread_name
    
    async def _create_thread(self, url: str, message: discord.Message) -> discord.Thread:
        """
        Create a new thread for a URL.
        
        Args:
            url: The URL
            message: The original message
            
        Returns:
            The created thread
        """
        
        thread_name = self._generate_default_thread_name(url)
        # Create the thread
        thread = await message.create_thread(name=thread_name)
        
        # Send initial message
        await thread.send(strings.DISCORD_THREAD_CREATED.format(url=url))
        
        # Update thread URL in cache if updater is available
        # if hasattr(self, '_thread_url_updater'):
        #     thread_url = f"https://discord.com/channels/{message.guild.id}/{thread.id}"
        #     await self._thread_url_updater(url, thread_url)
        
        return thread
        
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
                try:
                    logger.info(f"Processing URL: {url} from message {message.id}")
                    await self._process_url(url, message)
                except Exception as e:
                    logger.error(f"Error processing URL {url}: {e}")
    
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
    
    async def _check_duplicate_by_content_id(self, content_id: str) -> Optional[discord.Thread]:
        """
        Check if content with the given ID has already been processed.
    
        Args:
            content_id: The content ID to check
        
        Returns:
            The existing thread if the content ID is a duplicate, None otherwise
        """
        # Use the duplicate checker if available
        if hasattr(self, '_duplicate_checker'):
            logger.info(f"Checking for duplicates with content ID: {content_id}")
            existing_summary = await self._duplicate_checker(content_id)
            if existing_summary and existing_summary.thread_url:
                # Get the thread ID from the thread URL
                # Thread URLs are in the format: https://discord.com/channels/{guild_id}/{channel_id}/{thread_id}
                try:
                    thread_id = int(existing_summary.thread_url.split('/')[-1])
                    thread = self.get_channel(thread_id)
                    if thread:
                        return thread
                except (ValueError, IndexError):
                    logger.warning(f"Invalid thread URL in cache: {existing_summary.thread_url}")
    
        # No duplicate found or thread not accessible
        return None

    async def _process_url(self, url: str, message: discord.Message) -> None:
        """
        Process a URL from a message.
    
        Args:
            url: The URL to process
            message: The original message
            is_from_queue: Whether this URL is being processed from the queue
        """
        # Check if the URL is supported
        if not await self._is_supported_url(url):
            return
            
        # Extract ID
        content_id = await self._content_id_extractor(url)

        if not content_id:
            await message.reply(
                strings.DISCORD_ID_EXTRACTION_FAILED.format(url=url)
            )
            raise ValueError(f"Could not extract content ID from URL: {url}")
        
        # Check for duplicates
        processed_thread = await self._check_duplicate_by_content_id(content_id)
        if processed_thread:
            # Notify about duplicate
            thread_url = f"https://discord.com/channels/{message.guild.id}/{processed_thread.id}"
            await message.reply(
                strings.DISCORD_DUPLICATE_DETECTED.format(thread_url=thread_url)
            )
            return
        else:
            # Retrieve the existing thread or create a new one if none exists
            existing_thread = hasattr(message, 'thread') and message.thread
            if existing_thread:
                thread = message.thread
                await thread.send(strings.CONTENT_FETCHING)
                #  If existing thread, if the name is still the default one, it needs to be renamed
                default_thread_name = self._generate_default_thread_name(url)
                thread_rename_needed = thread.name == default_thread_name
            else:
                thread_rename_needed = True
                thread = await self._create_thread(url, message)
               
        
        try:
            # Fetch content
            if not self._content_processor:
                logger.error("Content processor not set")
                await thread.send("Error: Content processor not configured")
                raise RuntimeError("Content processor not configured")
                
            content_item = await self._content_processor(url)
            
            if not content_item:
                await thread.send(f"Could not fetch content from {url}")
                raise ValueError(f"Could not fetch content from {url}")
                
            # await thread.send(strings.DISCORD_CONTENT_FETCHED.format(type=content_item.type))
            
            # Summarize content
            if not self._summarizer:
                logger.error("Summarizer not set")
                await thread.send("Error: Summarizer not configured")
                raise RuntimeError("Summarizer not configured")
                
            # await thread.send(strings.SUMMARIZATION_PROCESSING)
            summary = await self._summarizer(content_item, thread.jump_url)
            
            
            if not summary:
                await thread.send("Could not generate summary")
                raise ValueError("Could not generate summary")
            
            formatted_summary = format_summary_for_discord(summary)
            if thread_rename_needed:
                new_thread_name = f"Discussion : {content_item.title}"[:self.THREAD_NAME_LIMIT]  # Limit to Discord thread name length
                await thread.edit(name=new_thread_name, locked=False)
            
            
            # Send to targets, including Discord
            if not self._target_handler:
                logger.error("Target handler not set")
                await thread.send("Error: Target handler not configured")
                raise RuntimeError("Target handler not configured")
                
            await self._target_handler(url, formatted_summary, thread, summary)

            return summary
            
        except Exception as e:
            logger.exception(f"Error processing URL {url}: {e}")
            await thread.send(strings.DISCORD_ERROR_FETCHING.format(url=url, error=str(e)))
            # Re-raise the exception for the queue processor to handle
            raise
    async def _scan_channel_messages(self, channel, days_back: int) -> dict:
        """
        Scan messages in a channel for supported links.
        
        Args:
            channel: The Discord channel to scan
            days_back: Number of days back to scan
            
        Returns:
            Dictionary with scan statistics
        """
        logger.info(f"Scanning messages in channel {channel.name} for the past {days_back} days")
        
        # Calculate the cutoff time
        cutoff_time = discord.utils.utcnow() - datetime.timedelta(days=days_back)
        
        # Initialize counters
        scanned = 0
        already_processed = 0
        not_processed = 0
        
        # Initialize list to store unprocessed URLs
        unprocessed_urls = []
        
        # Fetch messages from the channel
        async for message in channel.history(limit=None, after=cutoff_time):
            # Skip messages from the bot itself
            if message.author == self.user:
                continue
            
            # Skip messages in threads - we only want messages directly in the channel
            # Messages that start threads will be in the channel, not in the thread itself
            if hasattr(message, 'channel') and isinstance(message.channel, discord.Thread):
                continue
            
            scanned += 1
            
            # Extract URLs from the message content
            urls = await self._extract_urls(message.content)
            
            # Check if any of the URLs are supported
            for url in urls:
                if await self._is_supported_url(url):
                    logger.info(f"Found supported URL: {url} in message {message.id}")
                    
                    # Extract content ID
                    content_id = await self._content_id_extractor(url)
                    if not content_id:
                        logger.warning(f"Could not extract content ID from URL: {url}")
                        continue
                    
                    # Check if URL has already been processed
                    existing_thread = None
                    if hasattr(self, '_duplicate_checker'):
                        existing_summary = await self._duplicate_checker(content_id)
                        if existing_summary and existing_summary.thread_url:
                            try:
                                thread_id = int(existing_summary.thread_url.split('/')[-1])
                                existing_thread = self.get_channel(thread_id)
                            except (ValueError, IndexError):
                                logger.warning(f"Invalid thread URL in cache: {existing_summary.thread_url}")
                    
                    if existing_thread:
                        logger.info(f"URL already processed: {url}, thread: {existing_thread.id}")
                        already_processed += 1
                    else:
                        logger.info(f"URL not yet processed: {url}")
                        not_processed += 1
                        
                        # Store information about the unprocessed URL
                        thread_id = message.thread.id if hasattr(message, 'thread') and message.thread else None
                        unprocessed_urls.append({
                            "url": url,
                            "content_id": content_id,
                            "message_id": message.id,
                            "thread_id": thread_id,
                            "channel_id": message.channel.id,
                            "timestamp": message.created_at.isoformat()
                        })
        
        # Save unprocessed URLs to a JSON file
        if unprocessed_urls:
            try:
                # Create directory if it doesn't exist
                os.makedirs('data', exist_ok=True)
                
                # Generate filename with timestamp
                filename = f"data/unprocessed_urls.json"
                
                # Load existing unprocessed URLs if the file exists
                existing_urls = []
                if os.path.exists(filename):
                    try:
                        with open(filename, 'r', encoding='utf-8') as f:
                            existing_urls = json.load(f)
                        if not isinstance(existing_urls, list):
                            logger.warning(f"Existing file {filename} does not contain a list. Creating new file.")
                            existing_urls = []
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse existing file {filename}. Creating new file.")
                        existing_urls = []
                
                if len(existing_urls) > 0:
                    # Filter out duplicates before appending new unprocessed URLs
                    existing_content_ids = [url["content_id"] for url in existing_urls]
                    new_unique_urls = [url for url in unprocessed_urls if url["content_id"] not in existing_content_ids]
                    
                    # Append new unique URLs to existing ones
                    combined_urls = existing_urls + new_unique_urls

                                    # Log information about duplicates
                    if len(new_unique_urls) > 0:
                        logger.info(f"New unique URLs: {len(new_unique_urls)}")
                    else:
                        logger.info("No new unique URLs found.")
                    new_unprocessed_urls_count = len(new_unique_urls)
                else:
                    combined_urls = unprocessed_urls
                    new_unprocessed_urls_count = len(unprocessed_urls)
                
                # Write combined list to file
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(combined_urls, f, indent=2)
                    
                logger.info(f"Added {new_unprocessed_urls_count} unprocessed URLs to {filename} (total: {len(combined_urls)})")
            except Exception as e:
                logger.error(f"Error saving unprocessed URLs to file: {e}")
        
        # Return statistics
        return {
            "scanned": scanned,
            "processed": already_processed,
            "not_processed": not_processed
        }

    async def _check_moderator_permissions(self, ctx) -> bool:
        """
        Check if the user has moderator permissions in the channel.
        
        Args:
            ctx: The command context
        
        Returns:
            True if the user has moderator permissions, False otherwise
        """
        # # Check if the user is the server owner
        # if ctx.guild and ctx.author == ctx.guild.owner:
        #     return True
        
        # # Check if the user has administrator permissions
        # if ctx.guild and ctx.author.guild_permissions.administrator:
        #     return True
        
        # # Check if the user has manage_messages permission (common moderator permission)
        # if ctx.guild and ctx.author.permissions_in(ctx.channel).manage_messages:
        #     return True
        
        # User doesn't have moderator permissions
        # logger.info(f"User {ctx.author.name} ({ctx.author.id}) attempted to use a moderator command without permissions")
        # Temporary
        # return False
        return ctx.author.id == 909150160888664094
            
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

def format_summary_for_discord(summary_item: SummaryItem) -> str:
    """
    Format a SummaryItem as a Discord-friendly table.
    
    Args:
        summary_item: The SummaryItem to format
        
    Returns:
        A string containing the formatted summary for Discord
    """
    # Create a Discord-formatted table using Markdown
    table = "# Résumé pour " + summary_item.title + "\n\n"
    
    # Add the summary section
    table += summary_item.summary + "\n\n"
    
    # Add tags section
    if summary_item.tags:
        table += "\n## Tags :\n"
        tags_formatted = ", ".join([f"`{tag}`" for tag in summary_item.tags])
        table += tags_formatted + "\n"
    
    return table
