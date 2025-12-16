"""
JWT Authentication module for Item Service
"""

import os
import jwt
import requests
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://keycloak-dev.ltu-m7011e-10.se")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "BBosch")
CERTS_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
INSECURE = os.getenv("INSECURE", "false").lower() == "true"

security = HTTPBearer()
public_keys = None


def get_public_keys():
    """Fetch public keys from Keycloak for token verification"""
    global public_keys
    if not public_keys:
        try:
            response = requests.get(CERTS_URL, verify=not INSECURE, timeout=10)
            response.raise_for_status()
            public_keys = response.json()
        except requests.RequestException:
            raise HTTPException(
                status_code=503, detail="Authentication service unavailable"
            )
    return public_keys


def verify_jwt_token(token: str):
    """Verify and decode JWT token"""
    try:
        public_keys = get_public_keys()
        payload = jwt.decode(
            token, public_keys, algorithms=["RS256"], options={"verify_aud": False}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(
            status_code=503, detail="Authentication service unavailable"
        )


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency for authentication"""
    token_data = verify_jwt_token(credentials.credentials)
    return token_data


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency for admin authentication"""
    token_data = verify_jwt_token(credentials.credentials)

    # Check admin role
    user_roles = token_data.get("realm_access", {}).get("roles", [])
    if "admin" not in user_roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    return token_data
