import os


class Settings:
    """Configuration loaded from environment variables"""

    def __init__(self):
        # Supabase
        self.supabase_url = os.getenv("SUPABASE_URL", "https://test.supabase.co")
        self.supabase_key = os.getenv("SUPABASE_KEY", "test-key")

        # Other services
        self.products_service_url = os.getenv("PRODUCTS_SERVICE_URL", "http://localhost:8001")

        # Service settings
        self.service_name = "payments-service"
        self.host = "0.0.0.0"
        self.service_port = 8002
        self.log_level = os.getenv("LOG_LEVEL", "INFO")


# Create single settings instance
settings = Settings()
