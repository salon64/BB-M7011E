import os


class Settings:
    """Configuration loaded from environment variables"""

    def __init__(self):
        # Supabase
        self.supabase_url = os.getenv("SUPABASE_URL", "https://test.supabase.co")
        self.supabase_key = os.getenv("SUPABASE_KEY", "test-key")

        # Keycloak
        self.keycloak_url = os.getenv(
            "KEYCLOAK_URL", "https://keycloak.ltu-m7011e-10.se"
        )
        self.keycloak_realm = os.getenv("KEYCLOAK_REALM", "BBosch")
        self.keycloak_admin_user = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
        self.keycloak_admin_pass = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "BBadmin")
        self.keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID", "item-service")
        self.keycloak_client_secret = os.getenv(
            "KEYCLOAK_CLIENT_SECRET", "YOUR_ITEM_SERVICE_CLIENT_SECRET"
        )
        self.keycloak_callback_uri = os.getenv(
            "KEYCLOAK_CALLBACK_URI", "https://item-service.ltu-m7011e-10.se/callback"
        )

        # Service settings
        self.service_name = "item-service"
        self.host = "0.0.0.0"
        self.service_port = 8004  # Different port from user-service
        self.log_level = os.getenv("LOG_LEVEL", "DEBUG")


# Create single settings instance
settings = Settings()
