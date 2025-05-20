import json
import os
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class DiscordConfig(BaseModel):
    token: str
    monitored_channels: List[str]
    command_prefix: str = "!pia"

class YouTubeConfig(BaseModel):
    api_key: str
    proxy_enabled: bool = False
    proxy_http_url: str = ""
    proxy_https_url: str = ""

class ContentConfig(BaseModel):
    supported_domains: List[str]
    youtube: YouTubeConfig

class SummarizationConfig(BaseModel):
    provider: str = "claude"
    api_key: str
    model: str = "claude-2"
    max_tokens: int = 1000

class CodaConfig(BaseModel):
    api_key: str
    doc_id: str
    table_id: str
    tag_table_id: str  # Added tag table ID

class TargetConfig(BaseModel):
    coda: CodaConfig
    discord: Dict[str, Any] = Field(default_factory=lambda: {"enabled": True})

class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: Optional[str] = "pia-discord-bot.log"

class CacheConfig(BaseModel):
    file: str = "summary_cache.json"
    sync_interval_minutes: int = 30  # Default to 30 minutes

class BotConfig(BaseModel):
    discord: DiscordConfig
    content: ContentConfig
    summarization: SummarizationConfig
    target: TargetConfig
    cache: CacheConfig
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @field_validator('logging', mode='before')
    @classmethod
    def setup_logging(cls, v):
        # Configure logging based on the provided config
        log_config = v or LoggingConfig()
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        log_file = log_config.get('file')
        
        logging_handlers = []
        if log_file:
            logging_handlers.append(logging.FileHandler(log_file))
        logging_handlers.append(logging.StreamHandler())
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=logging_handlers
        )
        return v

class ConfigurationError(Exception):
    """Exception raised for errors in the configuration."""
    pass

class Config:
    """Configuration manager for the PIA Discord Bot using Pydantic."""
    
    _instance = None
    _config: Optional[BotConfig] = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one config instance exists."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def load(self, config_path: str = 'pia-discord-bot_config.json') -> None:
        """
        Load configuration from the specified JSON file.
        
        Args:
            config_path: Path to the configuration file
            
        Raises:
            ConfigurationError: If the configuration file is invalid or missing required fields
        """
        try:
            if not os.path.exists(config_path):
                raise ConfigurationError(f"Configuration file not found: {config_path}")
                
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            # Parse and validate the configuration using Pydantic
            self._config = BotConfig(**config_data)
            
            logging.info(f"Configuration loaded successfully from {config_path}")
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration: {e}")
    
    def get_discord(self) -> DiscordConfig:
        """Get Discord configuration."""
        self._ensure_loaded()
        return self._config.discord
    
    def get_content(self) -> ContentConfig:
        """Get content configuration."""
        self._ensure_loaded()
        return self._config.content
    
    def get_summarization(self) -> SummarizationConfig:
        """Get summarization configuration."""
        self._ensure_loaded()
        return self._config.summarization
    
    def get_target(self) -> TargetConfig:
        """Get target configuration."""
        self._ensure_loaded()
        return self._config.target
    
    def get_logging(self) -> LoggingConfig:
        """Get logging configuration."""
        self._ensure_loaded()
        return self._config.logging
    
    def get_cache_config(self) -> CacheConfig:
        """Get cache configuration."""
        self._ensure_loaded()
        return self._config.cache
    
    def _ensure_loaded(self) -> None:
        """Ensure configuration is loaded."""
        if self._config is None:
            raise ConfigurationError("Configuration not loaded. Call load() first.")
        
    def get_cache_file(self) -> str:
        """Get the cache file path from config."""
        self._ensure_loaded()
        return self._config.cache.file

# Create a singleton instance
config = Config()
