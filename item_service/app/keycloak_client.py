import requests
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def get_admin_token():
    """
    Get an admin token from Keycloak for administrative operations.
    """
    url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token"

    payload = {
        "client_id": "admin-cli",
        "username": settings.keycloak_admin_user,
        "password": settings.keycloak_admin_pass,
        "grant_type": "password",
    }

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        logger.error(f"Failed to get admin token: {e}")
        raise
