# Import OpenAI library
import openai
import logging
import json
import re
from typing import Dict, List 
from Modules.Commons import config, ContentItem, SummaryItem, sanitize_for_logging

logger = logging.getLogger(__name__)
        
# ChatGPT summarizer implementation
async def summarize_with_chatgpt(content_item: ContentItem) -> SummaryItem:
    """
    Summarize content using OpenAI's ChatGPT API.
    
    Args:
        content_item: The ContentItem to summarize
        
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
       
        prompt = f"""
I need you to summarize the following YouTube video:

Title: {title}
Creator: {author}

Content:
{main_content}

Please provide:
1. A concise summary (3-5 paragraphs) of the main points and key information. This summary MUST be in french, regardless of the content original language.
2. A list of 5-10 relevant tags or keywords, including the names of people mentioned
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
            title=content_item.title,
            author=content_item.author,
            url=content_item.url,
            summary=summary,
            tags=tags
        )
        
    except Exception as e:
        logger.exception(f"Error in ChatGPT summarization: {e}")
        raise RuntimeError(f"ChatGPT summarization failed: {str(e)}")
