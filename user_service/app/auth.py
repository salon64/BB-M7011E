"""
JWT Authentication module for Payment Service
"""

import os
import ssl
import jwt
from jwt import PyJWKClient
import requests
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://keycloak.ronstad.se")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "BB")
CERTS_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
INSECURE = os.getenv("INSECURE", "false").lower() == "true"

security = HTTPBearer()
jwks_client: Optional[PyJWKClient] = None


def get_jwks_client() -> PyJWKClient:
    """Get or create JWKS client for token verification"""
    global jwks_client
    if not jwks_client:
        try:
            if INSECURE:
                # Create SSL context that ignores certificate verification
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                jwks_client = PyJWKClient(CERTS_URL, ssl_context=ssl_context)
            else:
                jwks_client = PyJWKClient(CERTS_URL)
        except Exception as e:
            error_msg = f"Failed to create JWKS client for {CERTS_URL}: {str(e)}"
            print(f"ERROR: {error_msg}", file=__import__('sys').stderr)
            raise HTTPException(status_code=503, detail=error_msg)
    return jwks_client


def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        client = get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token, signing_key.key, algorithms=["RS256"], options={"verify_aud": False}
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        error_msg = f"Token expired: {str(e)}"
        print(f"ERROR: {error_msg}", file=__import__('sys').stderr)
        raise HTTPException(status_code=401, detail=error_msg)
    except jwt.InvalidTokenError as e:
        error_msg = f"Invalid token: {str(e)}"
        print(f"ERROR: {error_msg}", file=__import__('sys').stderr)
        raise HTTPException(status_code=401, detail=error_msg)
    except HTTPException:
        raise  # Re-raise HTTPException from get_public_keys()
    except Exception as e:
        error_msg = f"Unexpected error verifying token: {str(e)}"
        print(f"ERROR: {error_msg}", file=__import__('sys').stderr)
        raise HTTPException(
            status_code=503, detail=error_msg
        )


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """FastAPI dependency for authentication"""
    token_data = verify_jwt_token(credentials.credentials)
    return token_data


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """FastAPI dependency for admin authentication"""
    token_data = verify_jwt_token(credentials.credentials)

    # Check admin role
    user_roles = token_data.get("realm_access", {}).get("roles", [])
    if "admin" not in user_roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    return token_data

def get_admin_token() -> str:
    url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token"
    data = {
        "grant_type": "password",
        "client_id": "admin-cli",
        "username": settings.keycloak_admin_user,
        "password": settings.keycloak_admin_pass,
    }
    resp = requests.post(url, data=data)
    try:
        resp.raise_for_status()
    except Exception as e:
        print("Keycloak token error:", resp.status_code, resp.text)
        raise
    return resp.json()["access_token"]
