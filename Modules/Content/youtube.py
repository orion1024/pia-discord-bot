import logging
from datetime import datetime
import re
from typing import Optional, List, Dict, Any, Tuple
import asyncio
from pytubefix import YouTube
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

from Modules import strings
from Modules.Commons import sanitize_for_logging, ContentItem

logger = logging.getLogger(__name__)

_PLATFORM_NAME = "YouTube"


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract the YouTube video ID from a URL.
    
    Args:
        url: The YouTube URL
        
    Returns:
        The video ID if found, None otherwise
    """
    # Common YouTube URL patterns
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',  # Standard YouTube URLs
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',  # Short youtu.be URLs
        r'(?:embed\/)([0-9A-Za-z_-]{11})',  # Embed URLs
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})'  # Watch URLs
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            full_id = _PLATFORM_NAME + "/" + match.group(1)
            return full_id
    
    return None

async def process_youtube(url: str) -> Optional[ContentItem]:
    """
    Process a YouTube URL to extract video information and transcript.
    
    Args:
        url: The YouTube URL
        
    Returns:
        A ContentItem containing the video information and transcript
        
    Raises:
        RuntimeError: If processing fails
    """
    logger.info(strings.CONTENT_YOUTUBE_FETCHING)
    
    try:
            
        # Run pytube in a thread pool to avoid blocking the event loop
        def extract_info():
            yt = YouTube(url, client="WEB")
            return {
                "title": yt.title,
                "author": yt.author,
                "description": yt.description,
                "publish_date": yt.publish_date,
                "length": yt.length,
                "views": yt.views,
                "rating": yt.rating,
                "keywords": yt.keywords,
                "thumbnail_url": yt.thumbnail_url,
                "video_id": yt.video_id,
                "channel_id": yt.channel_id,
                "channel_url": yt.channel_url,
            }
        
        # Run the extraction in a thread pool
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, extract_info)
        
        # Get transcript using youtube_transcript_api
        transcript_text = await get_transcript(info["video_id"])

        full_content = f"===== Video description BEGIN =====\n\n{info['description']}\n\n"
        full_content += f"===== Video description END =====\n\n"
        if transcript_text:
            full_content += f"===== Video transcript BEGIN =====\n\n{transcript_text}\n\n"
            full_content += f"===== Video transcript END =====\n\n"
        
        # Extract full video ID from URL
        full_content_id = extract_video_id(url)
        
        # Create a ContentItem
        content_item = ContentItem(
            type=_PLATFORM_NAME,
            content_id=full_content_id,
            url=url,
            title=info["title"],
            author=info["author"],
            date=info["publish_date"] or datetime.now(),
            content=full_content,
            metadata={
                "video_id": info["video_id"],
                "content_id": f"youtube:{info['video_id']}",  # Add a standardized content_id
                "description": info["description"],
                "transcript": transcript_text,  # Store full transcript in metadata
                "duration": info["length"],
                "views": info["views"],
                "rating": info["rating"],
                "keywords": info["keywords"],
                "thumbnail_url": info["thumbnail_url"],
                "channel_id": info["channel_id"],
                "channel_url": info["channel_url"]
            }
        )
        




        logger.info(strings.CONTENT_YOUTUBE_FETCHED.format(title=sanitize_for_logging(content_item.title)))
        
        return content_item
        
    except Exception as e:
        logger.exception(f"Error processing YouTube URL {url}: {e}")
        raise RuntimeError(f"Failed to process YouTube URL: {str(e)}")

async def get_transcript(video_id: str) -> Optional[str]:
    """
    Get the transcript for a YouTube video using the latest API pattern.
    
    Args:
        video_id: The YouTube video ID
        
    Returns:
        The transcript text, or None if no transcript is available
    """
    try:
        # Run in a thread pool to avoid blocking
        def fetch_transcript():
            # Using the current API pattern from the latest documentation
            transcript = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get the transcript in the default language (usually the original language)
            default_transcript = transcript.find_transcript(['fr','en'])

            transcript_data = default_transcript.fetch()

            # Join all transcript segments into a single string
            return "\n".join([entry.text for entry in transcript_data])
            
        loop = asyncio.get_event_loop()
        transcript = await loop.run_in_executor(None, fetch_transcript)
        return transcript
        
    except NoTranscriptFound:
        logger.info(f"No transcript available for video {video_id}")
        return None
    except TranscriptsDisabled:
        logger.info(f"Transcripts are disabled for video {video_id}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching transcript for video {video_id}: {e}")
        return None