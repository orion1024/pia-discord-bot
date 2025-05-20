import logging
import requests
from datetime import datetime
import re
from typing import Optional, List, Dict, Any, Tuple
import asyncio
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.proxies import GenericProxyConfig

from Modules import strings
from Modules.Commons import config, sanitize_for_logging, ContentItem

logger = logging.getLogger(__name__)

_PLATFORM_NAME = "YouTube"

def get_youtube_metadata(video_id: str, api_key) -> Dict[str, Any]:
    url = f"https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,contentDetails,statistics",
        "id": video_id,
        "key": api_key
    }
    
    response = requests.get(url, params=params)
    return response.json()

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
        # Extract video ID from URL
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {url}")
        
        # Remove platform prefix to get the actual YouTube video ID
        youtube_video_id = video_id.split('/')[-1] if '/' in video_id else video_id
        
        
        # Get API key from config
        api_key = config.get_content().youtube.api_key
        if not api_key:
            raise ValueError("YouTube API key not found in configuration")
        
        # Get metadata using YouTube Data API
        metadata = get_youtube_metadata(youtube_video_id, api_key)
        
        if not metadata or 'items' not in metadata or not metadata['items']:
            raise ValueError(f"Could not fetch metadata for video ID: {youtube_video_id}")
        
        # Extract relevant information from the API response
        video_data = metadata['items'][0]
        snippet = video_data.get('snippet', {})
        statistics = video_data.get('statistics', {})
        content_details = video_data.get('contentDetails', {})
        
        # Parse duration from ISO 8601 format (PT1H2M3S) to seconds
        duration_str = content_details.get('duration', 'PT0S')
        duration_seconds = 0
        
        # Simple parsing of PT1H2M3S format
        hours = re.search(r'(\d+)H', duration_str)
        minutes = re.search(r'(\d+)M', duration_str)
        seconds = re.search(r'(\d+)S', duration_str)
        
        if hours:
            duration_seconds += int(hours.group(1)) * 3600
        if minutes:
            duration_seconds += int(minutes.group(1)) * 60
        if seconds:
            duration_seconds += int(seconds.group(1))
        
        # Format publish date
        publish_date_str = snippet.get('publishedAt')
        publish_date = None
        if publish_date_str:
            try:
                publish_date = datetime.fromisoformat(publish_date_str.replace('Z', '+00:00'))
            except ValueError:
                publish_date = datetime.now()
        else:
            publish_date = datetime.now()
        
        # Extract information
        info = {
            "title": snippet.get('title', 'Unknown Title'),
            "author": snippet.get('channelTitle', 'Unknown Author'),
            "description": snippet.get('description', ''),
            "publish_date": publish_date,
            "length": duration_seconds,
            "views": int(statistics.get('viewCount', 0)),
            "rating": float(statistics.get('likeCount', 0)) / 100,  # Approximate rating
            "keywords": snippet.get('tags', []),
            "thumbnail_url": snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
            "video_id": youtube_video_id,
            "channel_id": snippet.get('channelId', ''),
            "channel_url": f"https://www.youtube.com/channel/{snippet.get('channelId', '')}",
        }
        
        # Get transcript using youtube_transcript_api
        transcript_text = await get_transcript(youtube_video_id)

        full_content = f"===== Video description BEGIN =====\n\n{info['description']}\n\n"
        full_content += f"===== Video description END =====\n\n"
        if transcript_text:
            full_content += f"===== Video transcript BEGIN =====\n\n{transcript_text}\n\n"
            full_content += f"===== Video transcript END =====\n\n"
        else:
            logger.error("No transcript available for video: {video_id}. Aborting.")
            return None
        
        # Create a ContentItem
        content_item = ContentItem(
            type=_PLATFORM_NAME,
            content_id=video_id,
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

            youtube_config = config.get_content().youtube
            if youtube_config.proxy_enabled:
                logger.info(f"Proxy enabled, using proxy: {youtube_config.proxy_https_url}")
                proxy_config = GenericProxyConfig(
                                    http_url=youtube_config.proxy_http_url,
                                    https_url=youtube_config.proxy_https_url,
                                )
                ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
            else: 
                ytt_api = YouTubeTranscriptApi()
            
            transcript_list = ytt_api.list_transcripts(video_id)
            
            # Try to get the transcript in the default language (usually the original language)
            default_transcript = transcript_list.find_transcript(['fr','en'])

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