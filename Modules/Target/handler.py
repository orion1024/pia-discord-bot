import logging
from typing import Dict, Any, Callable, Awaitable, List
import discord

from Modules.Commons import config
from Modules import strings

logger = logging.getLogger(__name__)

# Type definition for target handler functions
TargetHandlerFunc = Callable[[str, str, Dict[str, Any]], Awaitable[None]]

class TargetHandler:
    """
    Target handler for sending summaries to various targets.
    Supports multiple targets through registered handler functions.
    """
    
    def __init__(self):
        """Initialize the target handler with empty handler registry."""
        self._handlers: Dict[str, TargetHandlerFunc] = {}
        
    def register_handler(self, target: str, handler: TargetHandlerFunc) -> None:
        """
        Register a handler function for a specific target.
        
        Args:
            target: The target name (e.g., 'discord', 'coda')
            handler: The async function that handles sending to this target
        """
        self._handlers[target] = handler
        logger.info(f"Registered target handler for: {target}")
        
    async def send_to_targets(self, url: str, summary: str, context: Dict[str, Any]) -> None:
        """
        Send a summary to all configured targets.
        
        Args:
            url: The original URL
            summary: The generated summary
            context: Additional context (e.g., Discord thread)
            
        Raises:
            RuntimeError: If sending to a target fails
        """
        if not summary:
            logger.warning("Cannot send empty summary to targets")
            return
            
        # Get enabled targets from configuration
        target_config = config.get_target()
        
        # Track errors
        errors = []
        
        # Send to each registered target
        for target_name, handler in self._handlers.items():
            try:
                # Check if this target is enabled
                if target_name == "discord" and not target_config.discord.get("enabled", True):
                    continue
                    
                if target_name == "coda" and not hasattr(target_config, "coda"):
                    continue
                    
                # Send to this target
                logger.info(f"Sending summary to target: {target_name}")
                await handler(url, summary, context)
                
            except Exception as e:
                logger.exception(f"Error sending to target {target_name}: {e}")
                errors.append(f"{target_name}: {str(e)}")
                
        if errors:
            error_msg = ", ".join(errors)
            raise RuntimeError(f"Failed to send to some targets: {error_msg}")

# Discord target handler
async def send_to_discord(url: str, summary: str, context: Dict[str, Any]) -> None:
    """
    Send a summary to a Discord thread.
    
    Args:
        url: The original URL
        summary: The generated summary
        context: Additional context (must contain 'thread')
        
    Raises:
        ValueError: If the context is invalid
        RuntimeError: If sending fails
    """
    # This is a placeholder - actual implementation will be refined later
    logger.info("Sending summary to Discord")
    
    # Extract thread from context
    thread = context.get("thread")
    if not isinstance(thread, discord.Thread):
        raise ValueError("Discord context must contain a valid thread")
    
    try:
        # Format the summary message
        message = f"**{strings.DISCORD_SUMMARY_TITLE}**\n\n{summary}"
        
        # Send the summary to the thread
        await thread.send(message)
        
    except Exception as e:
        logger.exception(f"Error sending summary to Discord: {e}")
        raise RuntimeError(f"Failed to send summary to Discord: {str(e)}")

# Coda target handler
async def send_to_coda(url: str, summary: str, context: Dict[str, Any]) -> None:
    """
    Send a summary to a Coda table.
    
    Args:
        url: The original URL
        summary: The generated summary
        context: Additional context
        
    Raises:
        RuntimeError: If sending fails
    """
    # This is a placeholder - actual implementation will come later
    logger.info("Sending summary to Coda")
    
    # Get Coda configuration
    target_config = config.get_target()
    coda_config = target_config.coda
    
    try:
        # Placeholder for actual Coda API call
        logger.info(f"Would send to Coda doc {coda_config.doc_id}, table {coda_config.table_id}")
        
        # Log success
        logger.info(strings.CODA_TABLE_UPDATED.format(url=url))
        
    except Exception as e:
        logger.exception(f"Error sending summary to Coda: {e}")
        raise RuntimeError(f"Failed to send summary to Coda: {str(e)}")

def create_target_handler() -> TargetHandler:
    """
    Create and configure a target handler with registered handlers for supported targets.
    
    Returns:
        A configured TargetHandler instance
    """
    handler = TargetHandler()
    
    # Register handlers for supported targets
    handler.register_handler("discord", send_to_discord)
    handler.register_handler("coda", send_to_coda)
    
    return handler
