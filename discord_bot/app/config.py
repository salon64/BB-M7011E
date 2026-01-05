# Discord Bot Configuration
import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Bot configuration settings."""
    discord_token: str = os.getenv("DISCORD_TOKEN", "")
    command_prefix: str = os.getenv("COMMAND_PREFIX", "!")
    
    # Service URLs
    user_service_url: str = os.getenv("USER_SERVICE_URL", "http://user-service:8001")
    payment_service_url: str = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8002")
    item_service_url: str = os.getenv("ITEM_SERVICE_URL", "http://item-service:8003")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
