import os
from typing import List, Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""
    
    # Twitter API
    twitterapi_key: str = Field(..., env="TWITTERAPI_KEY")
    
    # OpenAI
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-3.5-turbo-instruct", env="OPENAI_MODEL")
    
    # Weaviate
    weaviate_url: str = Field("http://localhost:8080", env="WEAVIATE_URL")
    
    # Notification
    telegram_token: Optional[str] = Field(None, env="TELEGRAM_TOKEN")
    telegram_chat_id: Optional[str] = Field(None, env="TELEGRAM_CHAT_ID")
    notification_method: str = Field("console", env="NOTIFICATION_METHOD")
    
    # Application settings
    monitoring_interval: int = Field(300, env="MONITORING_INTERVAL")
    sentiment_threshold: int = Field(7, env="SENTIMENT_THRESHOLD")
    target_keywords: List[str] = Field(default_factory=lambda: ["BTC", "ETH", "SOL"])
    
    # Additional settings
    accounts_file: str = Field("accounts.csv", env="ACCOUNTS_FILE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Parse target keywords if provided as comma-separated string
        if isinstance(self.target_keywords, str):
            self.target_keywords = [k.strip() for k in self.target_keywords.split(",")]


# Create settings instance
settings = Settings()