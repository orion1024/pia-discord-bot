#!/usr/bin/env python3
import os
import sys
import logging
import asyncio
from typing import Dict, Any

from Modules.Commons import config, ConfigurationError
from Modules.Discord import create_bot, start_bot, PiaBot
from Modules.Content import create_content_processor
from Modules.Summarization import create_summarizer
from Modules.Target import create_target_handler

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
    
    # Connect the content processor to the bot
    async def process_content(url: str) -> Dict[str, Any]:
        """Process content from a URL."""
        return await content_processor.process(url)
    
    bot.set_content_processor(process_content)
    
    # Connect the summarizer to the bot
    async def summarize_content(content: Dict[str, Any]) -> str:
        """Summarize content."""
        return await summarizer.summarize(content)
    
    bot.set_summarizer(summarize_content)
    
    # Connect the target handler to the bot
    async def handle_targets(url: str, summary: str, thread) -> None:
        """Send summary to targets."""
        context = {"thread": thread}
        await target_handler.send_to_targets(url, summary, context)
    
    bot.set_target_handler(handle_targets)
    
    return bot

async def main_async():
    """Asynchronous main function."""
    try:
        # Load configuration
        config.load()
        
        # Set up and start the bot
        logging.info("PIA Discord Bot starting...")
        bot = await setup_bot()
        
        logging.info("PIA Discord Bot initialized successfully")
        await start_bot(bot)
        
    except ConfigurationError as e:
        logging.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Initialization error: {e}")
        sys.exit(1)

def main():
    """Main entry point for the application."""
    # Run the async main function
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
