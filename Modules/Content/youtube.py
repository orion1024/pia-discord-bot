import logging
from datetime import datetime
import re
from typing import Optional, List, Dict, Any
import asyncio
from pytubefix import YouTube
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

from .models import ContentItem
from Modules import strings
from Modules.Commons.commons import sanitize_for_logging

logger = logging.getLogger(__name__)

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
        # Extract video ID from URL
        video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
        if not video_id_match:
            raise ValueError(f"Could not extract video ID from URL: {url}")
            
        video_id = video_id_match.group(1)
        
        # Run pytube in a thread pool to avoid blocking the event loop
        def extract_info():
            yt = YouTube(url)
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
        transcript_text = await get_transcript(video_id)

        full_content = f"===== Video description BEGIN =====\n\n{info['description']}\n\n"
        full_content += f"===== Video description END =====\n\n"
        if transcript_text:
            full_content += f"===== Video transcript BEGIN =====\n\n{transcript_text}\n\n"
            full_content += f"===== Video transcript END =====\n\n"
        
        # Create a ContentItem
        content_item = ContentItem(
            type="youtube",
            url=url,
            title=info["title"],
            author=info["author"],
            date=info["publish_date"] or datetime.now(),
            content=full_content,
            metadata={
                "video_id": info["video_id"],
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
        
        # logger.info(f"YouTube content properties - Title: {sanitize_for_logging(content_item.title)}, Author: {content_item.author}, "
        #                    f"Date: {content_item.date}, URL: {content_item.url}, Video ID: {content_item.metadata['video_id']}, "
        #                    f"Duration: {content_item.metadata['duration']}s, Views: {content_item.metadata['views']}, "
        #                    f"Content: {content_item.content[:100]}...")        
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
            transcript_data = default_transcript.fetch().to_raw_data()

            # Join all transcript segments into a single string
            return "\n".join([entry["text"] for entry in transcript_data])
            
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