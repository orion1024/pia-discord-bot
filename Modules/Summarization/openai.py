# Import OpenAI library
import openai
import logging
import json
import re
from typing import Dict, List, Optional
from Modules.Commons import config, ContentItem, SummaryItem, sanitize_for_logging, TagInfo

logger = logging.getLogger(__name__)
        
# ChatGPT summarizer implementation
async def summarize_with_chatgpt(content_item: ContentItem, tag_info: Optional[Dict[str, TagInfo]] = None) -> SummaryItem:
    """
    Summarize content using OpenAI's ChatGPT API.
    
    Args:
        content_item: The ContentItem to summarize
        tag_info: Optional dictionary of TagInfo objects to help with tagging
        
    Returns:
        A SummaryItem containing the summary and metadata
        
    Raises:
        RuntimeError: If summarization fails
    """
    try:
        # Get OpenAI configuration
        summarization_config = config.get_summarization()
        
        # Set up OpenAI client
        client = openai.AsyncOpenAI(
            api_key=summarization_config.api_key,
        )
        
        # Prepare content for summarization based on content type
        content_type = content_item.type
        title = content_item.title
        author = content_item.author
        main_content = content_item.content
       
        # Prepare tag information if available
        tag_guidance = ""
        if tag_info and len(tag_info) > 0:
            tag_guidance = "Here is additional detailed tag guidance:\n"
            tag_guidance += "You will find below a list of tags and their description. The content will probably match one or several of them (but not always).\n"
            tag_guidance += "You can come up with other tags when appropriate, but if they are similar to the ones below, prioritize the latter.\n"
            tag_guidance += "If people or companies are mentioned in the content in any meaningful way, always include them as tags.\n"
            for tag, info in tag_info.items():
                if info.description:
                    tag_guidance += f"- {tag}: {info.description}\n"
                else:
                    tag_guidance += f"- {tag}\n"

        prompt = f"""
I need you to summarize the following YouTube video:

Title: {title}
Creator: {author}

Content:
{main_content}

Please provide:
1. A concise summary (3-5 paragraphs) of the main points and key information. This summary MUST be in french, regardless of the content original language.
2. A list of 5-10 relevant tags or keywords, including the names of people mentioned

{tag_guidance}

3. Format your response as a JSON object with the following structure:
{{
  "summary": "Your summary text here in french...",
  "tags": ["tag1", "tag2", "tag3", ...]
}}
"""
        # Call OpenAI API
        logger.info(f"Sending request to ChatGPT API for content: {sanitize_for_logging(title)}")
        
        response = await client.chat.completions.create(
            model=summarization_config.model or "gpt-4",
            temperature=0.3,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant that summarizes content accurately and concisely. Always respond with a JSON object containing 'summary' and 'tags' fields."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the response content
        response_content = response.choices[0].message.content
        
        # Parse the JSON response
        try:
            # Try to extract JSON from the response
            # First, look for JSON block in markdown
            json_match = re.search(r'(?:json)?\s*({.*?})\s*', response_content, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
            else:
                # If no markdown block, try to parse the whole response as JSON
                result = json.loads(response_content)
                
            summary = result.get("summary", "No summary provided.")
            tags = result.get("tags", [])
            
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Failed to parse JSON from ChatGPT response: {e}")
            # Fallback: use the whole response as summary
            summary = response_content
            tags = []
        
        # Create and return SummaryItem
        return SummaryItem(
            type=content_item.type,
            content_id=content_item.content_id,
            title=content_item.title,
            author=content_item.author,
            url=content_item.url,
            summary=summary,
            content=content_item.content,  # Include the original content
            tags=tags
        )        
    except Exception as e:
        logger.exception(f"Error in ChatGPT summarization: {e}")
        raise RuntimeError(f"ChatGPT summarization failed: {str(e)}")
