import os
import logging
import time
import requests
from common.database import get_supabase

logger = logging.getLogger(__name__)

# Keycloak configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://keycloak.ronstad.se")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "BB")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "discord-to-user")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
INSECURE = os.getenv("INSECURE", "false").lower() == "true"

# JWT cache settings - max TTL from env var (default: 1 day = 86400 seconds)
# Actual TTL will be the minimum of token's expires_in and this value
JWT_MAX_CACHE_TTL = int(os.getenv("JWT_CACHE_TTL", "86400"))

# Global JWT cache
_discord_jwt: str | None = None
_discord_jwt_expiry: float = 0.0  # Absolute expiry timestamp


class UserNotLinkedError(Exception):
    """Raised when a Discord user has not linked their account."""
    def __init__(self, discord_id: str):
        self.discord_id = discord_id
        super().__init__(f"User {discord_id} has not linked their account")


def get_discord_jwt() -> str | None:
    """
    Get a JWT for the Discord bot client from Keycloak.
    Uses a cached token if still valid, otherwise requests a new one.
    Token TTL is based on Keycloak's expires_in, capped by JWT_MAX_CACHE_TTL.
    Returns None if token request fails.
    """
    global _discord_jwt, _discord_jwt_expiry
    
    current_time = time.time()
    
    # Check if cached JWT is still valid (with 30 second buffer)
    if _discord_jwt and current_time < (_discord_jwt_expiry - 30):
        logger.debug("Using cached Discord JWT")
        return _discord_jwt
    
    # Request new JWT from Keycloak
    token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    
    data = {
        "grant_type": "client_credentials",
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
    }
    
    try:
        if INSECURE:
            logger.warning("INSECURE mode enabled: skipping SSL verification for Keycloak requests")
        
        resp = requests.post(
            token_url,
            data=data,
            verify=not INSECURE,
            timeout=15
        )
        
        if resp.status_code != 200:
            logger.error(f"Failed to get Discord JWT from Keycloak: {resp.status_code} - {resp.text}")
            return None
        
        token_data = resp.json()
        _discord_jwt = token_data.get("access_token")
        
        # Use expires_in from token, capped by max TTL
        expires_in = token_data.get("expires_in", JWT_MAX_CACHE_TTL)
        effective_ttl = min(expires_in, JWT_MAX_CACHE_TTL)
        _discord_jwt_expiry = current_time + effective_ttl
        
        logger.info(f"Successfully obtained new Discord JWT from Keycloak (expires in {effective_ttl}s)")
        return _discord_jwt
        
    except requests.RequestException as e:
        logger.error(f"Request to Keycloak failed: {e}")
        return None


def get_user_card_id(discord_id: str) -> str:
    """
    Get the card_id for a Discord user from Supabase.
    
    Args:
        discord_id: The Discord user ID to look up
        
    Returns:
        The user's card_id
        
    Raises:
        UserNotLinkedError: If no user exists with the given Discord ID
    """
    client = get_supabase()
    response = client.table("Users").select("card_id").eq("discord", discord_id).execute()
    
    if not response.data:
        logger.warning(f"No user found with discord_id: {discord_id}")
        raise UserNotLinkedError(discord_id)
    
    return response.data[0]["card_id"]