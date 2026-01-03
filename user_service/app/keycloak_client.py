import os
import requests
from app.config import settings
from app.auth import get_admin_token

def create_keycloak_user(username, email, first_name, last_name, password):
    import logging
    import traceback
    logger = logging.getLogger("keycloak_client")
    logger.info("create_keycloak_user called with username=%s, email=%s", username, email)
    token = get_admin_token()
    url = f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/users"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "username": username,
        "emailVerified": True,
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "enabled": True,
        "credentials": [
            {
                "type": "password",
                "value": password
            }
        ]
    }
    try:
        logger.debug("Sending POST to Keycloak: url=%s, headers=%s, payload=%s", url, headers, payload)
        resp = requests.post(url, json=payload, headers=headers)
        logger.debug("Keycloak response: status=%s, text=%s", resp.status_code, resp.text)
    except Exception as e:
        logger.error("Keycloak user creation exception: %s", str(e))
        logger.error("Traceback:\n%s", traceback.format_exc())
        raise
    if resp.status_code != 201:
        logger.error("Keycloak user creation failed: status=%s, body=%s", resp.status_code, resp.text)
    try:
        resp.raise_for_status()
    except Exception as e:
        logger.error("Keycloak user creation error: %s", str(e))
        logger.error("Status code: %s", getattr(e.response, 'status_code', 'N/A') if hasattr(e, 'response') else 'N/A')
        logger.error("Response text: %s", getattr(e.response, 'text', 'N/A') if hasattr(e, 'response') else 'N/A')
        logger.error("Traceback:\n%s", traceback.format_exc())
        raise
    logger.info("Keycloak user creation succeeded for username=%s", username)
    return resp.status_code == 201