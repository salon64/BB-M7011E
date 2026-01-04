import os
import sys
import requests
import jwt
from jwt import PyJWKClient
import json


def request_token(
    kc_url: str,
    realm: str,
    client_id: str,
    username: str,
    password: str,
    client_secret: str | None = None,
    insecure: bool = False,
) -> dict:
    token_url = f"{kc_url}/realms/{realm}/protocol/openid-connect/token"
    data = {
        "grant_type": "password",
        "client_id": client_id,
        "username": username,
        "password": password,
    }
    if client_secret:
        data["client_secret"] = client_secret
    
    print(f"Requesting token from: {token_url}")
    print(f"Client: {client_id}, Username: {username}")
    
    resp = requests.post(token_url, data=data, verify=not insecure, timeout=15)
    
    if resp.status_code != 200:
        print(f"Error response: {resp.text}", file=sys.stderr)
    
    resp.raise_for_status()
    return resp.json()


def decode_token(token: str) -> dict:
    """Decode JWT token without verification (for debugging)"""
    try:
        # Decode without verification to inspect payload
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        print(f"Failed to decode token: {e}", file=sys.stderr)
        return {}


def validate_token(token: str, kc_url: str, realm: str, insecure: bool = False) -> dict:
    """Validate JWT token by verifying signature with Keycloak's public key"""
    try:
        from jwt import PyJWKClient
        import ssl
        
        # Construct JWKS URL
        jwks_url = f"{kc_url}/realms/{realm}/protocol/openid-connect/certs"
        
        # Create SSL context that ignores certificate verification if insecure
        if insecure:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            client = PyJWKClient(jwks_url, ssl_context=ssl_context)
        else:
            client = PyJWKClient(jwks_url)
        
        signing_key = client.get_signing_key_from_jwt(token)
        
        # Decode and verify token
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
        
        return decoded
    except jwt.ExpiredSignatureError:
        print("Token has expired!", file=sys.stderr)
        return {}
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {e}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"Failed to validate token: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return {}


def main():
    kc_url = os.getenv("KC_URL", "https://keycloak.ronstad.se")
    realm = os.getenv("KC_REALM", "BB")
    client_id = os.getenv("KC_CLIENT_ID", "pubic-user")
    client_secret = "efYsbdlGLYesugyBIKpYayiKYloYgVaX"  # optional
    username = os.getenv("KC_USERNAME", "1212")
    password = os.getenv("KC_PASSWORD", "123")
    insecure = os.getenv("KC_INSECURE", "true").lower() == "true"

    try:
        tokens = request_token(kc_url, realm, client_id, username, password, client_secret, insecure)
    except Exception as e:
        print(f"Token request failed: {e}", file=sys.stderr)
        sys.exit(1)

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    
    print("\n" + "="*80)
    print("ACCESS TOKEN:")
    print("="*80)
    print(access_token)
    
    print("\n" + "="*80)
    print("DECODED ACCESS TOKEN (unverified):")
    print("="*80)
    decoded = decode_token(access_token)
    print(json.dumps(decoded, indent=2))
    
    print("\n" + "="*80)
    print("VALIDATED ACCESS TOKEN (signature verified):")
    print("="*80)
    validated = validate_token(access_token, kc_url, realm, insecure)
    if validated:
        print("✓ Token signature is VALID")
        print(json.dumps(validated, indent=2))
    else:
        print("✗ Token validation FAILED")
    
    print("\n" + "="*80)
    print("REFRESH TOKEN:")
    print("="*80)
    print(refresh_token)


if __name__ == "__main__":
    main()
