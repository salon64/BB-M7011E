from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration loaded from .env file"""

    # Supabase
    supabase_url: str
    supabase_key: str

    # Redis
    # redis_url: str

    # Other services
    products_service_url: str
    # auth_service_url: str

    # Service settings
    service_name: str = "payments-service"
    host: str = "0.0.0.0"
    service_port: int = 8002
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Create single settings instance
settings = Settings()
