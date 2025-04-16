from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional

@dataclass
class ContentItem:
    """
    Standardized content model for all content types.
    This ensures consistent structure for content processors and summarizers.
    """
    # Required properties
    type: str  # Source platform type (youtube, twitter, article, etc.)
    url: str   # Original URL
    title: str  # Content title
    author: str  # Main author/creator
    date: datetime  # Date of content creation
    content: str  # Primary text content
    
    # Optional metadata for platform-specific or additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize the content item after initialization."""
        # Ensure all required fields have at least empty values
        if not self.title:
            self.title = ""
        if not self.author:
            self.author = ""
        if not self.content:
            self.content = ""
        
        # Ensure date is a datetime object
        if isinstance(self.date, str):
            try:
                # Try to parse ISO format date
                self.date = datetime.fromisoformat(self.date.replace('Z', '+00:00'))
            except ValueError:
                # If parsing fails, use current time
                self.date = datetime.now()
        elif not isinstance(self.date, datetime):
            self.date = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the content item to a dictionary."""
        return {
            "type": self.type,
            "url": self.url,
            "title": self.title,
            "author": self.author,
            "date": self.date.isoformat(),
            "content": self.content,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentItem':
        """Create a ContentItem from a dictionary."""
        # Extract required fields
        content_type = data.get("type", "")
        url = data.get("url", "")
        title = data.get("title", "")
        author = data.get("author", "")
        date = data.get("date", datetime.now())
        content = data.get("content", "")
        
        # Extract metadata (all other fields)
        metadata = {k: v for k, v in data.items() 
                   if k not in ["type", "url", "title", "author", "date", "content"]}
        
        return cls(
            type=content_type,
            url=url,
            title=title,
            author=author,
            date=date,
            content=content,
            metadata=metadata
        )
