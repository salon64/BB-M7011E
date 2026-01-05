import os
import logging
import requests
from common.database import get_supabase

logger = logging.getLogger(__name__)

# Keycloak configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://keycloak.ronstad.se")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "BB")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "discord-to-user")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
INSECURE = os.getenv("INSECURE", "false").lower() == "true"


def get_user_jwt(discord_id: str) -> str | None:
    """Retrieve the JWT for a given user via supabase and keycloak. None if no user have matching discord_id."""    
    client = get_supabase()
    response = client.table("Users").select("card_id").eq("discord", discord_id).execute()
    if not response.data:
        logger.warning(f"No user found with discord_id: {discord_id}")
        return None
    card_id = response.data[0]["card_id"]
    
    # Get token from Keycloak using the card_id as the username
    # The discord-to-user client uses direct access grants to issue tokens for users
    token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    
    data = {
        "grant_type": "password",
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "username": card_id,
        "password": card_id,  # For card-based auth, password equals card_id
    }
    
    try:
        resp = requests.post(
            token_url,
            data=data,
            verify=not INSECURE,
            timeout=15
        )
        
        if resp.status_code != 200:
            logger.error(f"Failed to get token from Keycloak: {resp.status_code} - {resp.text}")
            return None
        
        token_data = resp.json()
        return token_data.get("access_token")
        
    except requests.RequestException as e:
        logger.error(f"Request to Keycloak failed: {e}")
        return None