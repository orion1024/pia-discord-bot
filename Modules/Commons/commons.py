def sanitize_for_logging(text):
    """Sanitize text for logging by removing problematic characters."""
    if not text:
        return ""
    
    # Handle non-string inputs
    if not isinstance(text, str):
        try:
            text = str(text)
        except:
            return "[Non-string content]"
    
    try:
        # Use a more aggressive approach: keep only ASCII characters
        # This will remove all non-ASCII characters instead of replacing them
        return ''.join(c for c in text if ord(c) < 128)
    except:
        # If that fails for any reason, return a safe string
        return "[Content with unsupported characters]"
