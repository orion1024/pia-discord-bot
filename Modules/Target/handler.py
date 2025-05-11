import logging
from typing import Dict, Any, Callable, Awaitable, List
import discord
import asyncio
from codaio import Coda, Document, Cell
from Modules.Commons import config, SummaryItem
from Modules import strings

logger = logging.getLogger(__name__)

# Type definition for target handler functions
TargetHandlerFunc = Callable[[str, str, Dict[str, Any], SummaryItem], Awaitable[None]]

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
        
    async def send_to_targets(self, url: str, summary: str, context: Dict[str, Any], summary_item: SummaryItem) -> None:
        """
        Send a summary to all configured targets.
        
        Args:
            url: The original URL
            summary: The generated summary
            context: Additional context (e.g., Discord thread)
            summary_item: The complete SummaryItem object
            
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
                await handler(url, summary, context, summary_item)
                
            except Exception as e:
                logger.exception(f"Error sending to target {target_name}: {e}")
                errors.append(f"{target_name}: {str(e)}")
                
        if errors:
            error_msg = ", ".join(errors)
            raise RuntimeError(f"Failed to send to some targets: {error_msg}")

# Discord target handler
async def send_to_discord(url: str, summary: str, context: Dict[str, Any], summary_item: SummaryItem) -> None:
    """
    Send a summary to a Discord thread.
    
    Args:
        url: The original URL
        summary: The generated summary
        context: Additional context (must contain 'thread')
        summary_item: The complete SummaryItem object
        
    Raises:
        ValueError: If the context is invalid
        RuntimeError: If sending fails
    """
    logger.info("Sending summary to Discord")
    
    # Extract thread from context
    thread = context.get("thread")
    if not isinstance(thread, discord.Thread):
        raise ValueError("Discord context must contain a valid thread")
    
    try:               
        # Send the summary to the thread
        await thread.send(summary)
        
    except Exception as e:
        logger.exception(f"Error sending summary to Discord: {e}")
        raise RuntimeError(f"Failed to send summary to Discord: {str(e)}")

# Coda target handler
async def send_to_coda(url: str, summary: str, context: Dict[str, Any], summary_item: SummaryItem) -> None:
    """
    Send a summary to a Coda table.
    
    Args:
        url: The original URL
        summary: The generated summary
        context: Additional context
        summary_item: The complete SummaryItem object
        
    Raises:
        RuntimeError: If sending fails
    """
    logger.info("Sending summary to Coda")
    
    # Get Coda configuration
    target_config = config.get_target()
    coda_config = target_config.coda
    
    try:
        # Run in a thread pool to avoid blocking the event loop
        def add_to_coda():
            # Initialize Coda client
            coda = Coda(coda_config.api_key)
            # Get the doc and table
            doc = Document(coda_config.doc_id, coda=coda)
            table = doc.get_table(coda_config.table_id)
            
            # Prepare cells for the row
            cells = []
            cells.append(Cell(column='URL', value_storage=summary_item.url))
            cells.append(Cell(column='Discord', value_storage=summary_item.thread_url))
            cells.append(Cell(column='Type', value_storage=summary_item.type))
            cells.append(Cell(column='ID', value_storage=summary_item.content_id))
            cells.append(Cell(column='Auteur', value_storage=summary_item.author))
            cells.append(Cell(column='Tags', value_storage=summary_item.tags))
            cells.append(Cell(column='Titre', value_storage=summary_item.title))
            cells.append(Cell(column='Résumé', value_storage=summary_item.summary))
            
            # cells = []
            # cells.append(Cell(column='URL', value_storage="test"))
            # cells.append(Cell(column='Discord', value_storage="https://discord.com/channels/1214198954321907842/1364567130762117180"))
            # cells.append(Cell(column='Type', value_storage="test"))
            # cells.append(Cell(column='ID', value_storage="test"))
            # cells.append(Cell(column='Auteur', value_storage="test"))
            # cells.append(Cell(column='Tags', value_storage="test"))
            # cells.append(Cell(column='Titre', value_storage="test"))
            # cells.append(Cell(column='Résumé', value_storage="test"))
            
             # Add tags if available
            if hasattr(summary_item, 'tags') and summary_item.tags:
                cells.append(Cell(column='Tags', value_storage=", ".join(summary_item.tags)))
            
            # Upsert the row to the table
            result = table.upsert_row(cells)
           
            return result
        
        # Run the Coda API call in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, add_to_coda)
        
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
    
    return handler
