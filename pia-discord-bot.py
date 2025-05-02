#!/usr/bin/env python3
import os
import sys
import logging
import asyncio
import signal
from typing import Dict, Any, Optional

from Modules.Commons import config, ConfigurationError, ContentItem, SummaryItem
from Modules.Discord import create_bot, start_bot, PiaBot
from Modules.Content import create_content_processor
from Modules.Summarization import create_summarizer
from Modules.Target import create_target_handler
from Modules.Cache import create_cache

# Global variables
bot_instance = None
shutdown_in_progress = False  # Flag to prevent multiple shutdown calls

async def setup_bot() -> PiaBot:
    """
    Set up and configure the Discord bot with all required components.
    
    Returns:
        A configured PiaBot instance
    """
    # Create instances of all components
    bot = create_bot()
    content_processor = create_content_processor()
    summarizer = create_summarizer()
    target_handler = create_target_handler()
    cache = create_cache()  # Create the cache
    
    # Connect the content ID extractor to the bot
    async def extract_content_id(url: str) -> Optional[str]:
        """Extract a standardized content ID from a URL."""
        return await content_processor.extract_content_id(url)

    bot.set_content_id_extractor(extract_content_id)

    # Connect the content processor to the bot
    async def process_content(url: str) -> ContentItem:
        """Process content from a URL."""
        return await content_processor.process(url)
    
    bot.set_content_processor(process_content)
    
    # Connect the summarizer to the bot
    async def summarize_content(content_item: ContentItem, thread_url: str) -> SummaryItem:
        """Summarize content."""
        summary_item = await summarizer.summarize(content_item)
        summary_item.thread_url = thread_url
        # Add to cache after summarization
        await cache.add_summary(summary_item)
        return summary_item
    
    bot.set_summarizer(summarize_content)
    
    # Connect the cache to the bot for duplicate detection
    async def check_duplicate(content_id: str) -> Optional[SummaryItem]:
        """Check if content has already been processed."""
        return cache.find_by_content_id(content_id)
    
    bot.set_duplicate_checker(check_duplicate)
    
    # Connect the target handler to the bot
    async def handle_targets(url: str, summary: str, thread, summary_item: SummaryItem) -> None:
        """Send summary to targets."""
        context = {"thread": thread}
        await target_handler.send_to_targets(url, summary, context, summary_item)
    
    bot.set_target_handler(handle_targets)
    
    # Store the bot instance globally for shutdown handling
    global bot_instance
    bot_instance = bot
    
    return bot

async def shutdown(signal=None):
    """
    Gracefully shut down the bot.
    
    Args:
        signal: The signal that triggered the shutdown (optional)
    """
    global shutdown_in_progress
    
    # Prevent multiple shutdown calls
    if shutdown_in_progress:
        return
    
    shutdown_in_progress = True
    
    if signal:
        logging.info(f"Received exit signal {signal.name}...")
    
    logging.info("Shutting down bot...")
    
    # Close the Discord connection if bot is running
    if bot_instance and bot_instance.is_ready():
        logging.info("Closing Discord connection...")
        await bot_instance.close()
    
    # Cancel all running tasks except the current one
    # tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    # if tasks:
    #     logging.info(f"Cancelling {len(tasks)} pending tasks...")
    #     for task in tasks:
    #         task.cancel()
        
    #     # Wait for tasks to be cancelled with a timeout
    #     try:
    #         await asyncio.wait(tasks, timeout=2)
    #     except Exception as e:
    #         logging.warning(f"Error while cancelling tasks: {e}")
    
    logging.info("Shutdown complete")

def handle_exit_signal(signum, frame):
    """
    Handle exit signals by stopping the event loop.
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    # Get the current event loop
    loop = asyncio.get_event_loop()
    
    # Schedule the shutdown coroutine
    loop.create_task(shutdown())
    
    # Stop the event loop after a short delay to allow shutdown to complete
    loop.call_later(2, loop.stop)

async def main_async():
    """Asynchronous main function."""
    try:
        # Load configuration
        config.load()
        
        # Set up and start the bot
        logging.info("PIA Discord Bot starting...")
        bot = await setup_bot()
        
        logging.info("PIA Discord Bot initialized successfully")
        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        try:
            # This works on Unix-like systems (Linux, macOS)
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(shutdown(s))
                )
            logging.info("Registered asyncio signal handlers")
        except NotImplementedError:
            # This fallback is needed for Windows
            logging.info("Asyncio signal handlers not supported on this platform, using signal.signal instead")
            # We'll rely on the signal.signal handlers set in the main function
            
        # Start the bot (this will block until the bot is stopped)
        await start_bot(bot)
        
    except ConfigurationError as e:
        logging.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Initialization error: {e}")
        sys.exit(1)
    finally:
        # Ensure shutdown is called even if an error occurs
        await shutdown()

def main():
    """Main entry point for the application."""
    # Register signal handlers for non-asyncio context
    signal.signal(signal.SIGINT, handle_exit_signal)
    signal.signal(signal.SIGTERM, handle_exit_signal)
    
    # Run the async main function
    try:
        # On Windows, use a specific event loop policy to avoid the shutdown error
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        asyncio.run(main_async())
    except KeyboardInterrupt:
        # This will be caught if Ctrl+C is pressed before asyncio.run starts
        logging.info("Interrupted by user")
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
