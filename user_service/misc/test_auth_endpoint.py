import os
import sys
import requests
import json


def get_token(kc_url: str, realm: str, client_id: str, username: str, password: str, client_secret: str | None = None, insecure: bool = False) -> str:
    """Get access token from Keycloak"""
    token_url = f"{kc_url}/realms/{realm}/protocol/openid-connect/token"
    data = {
        "grant_type": "password",
        "client_id": client_id,
        "username": username,
        "password": password,
    }
    if client_secret:
        data["client_secret"] = client_secret
    
    resp = requests.post(token_url, data=data, verify=not insecure, timeout=15)
    resp.raise_for_status()
    return resp.json().get("access_token")


def test_auth_endpoint(token: str, api_url: str, insecure: bool = False):
    """Test the /auth/jwt endpoint with the token"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    endpoint = f"{api_url}/auth/jwt"
    print(f"\nMaking request to: {endpoint}")
    print(f"Headers: Authorization: Bearer {token[:50]}...")
    
    resp = requests.get(endpoint, headers=headers, verify=not insecure, timeout=10)
    
    print(f"\nResponse Status: {resp.status_code}")
    print(f"Response Body:")
    print(json.dumps(resp.json(), indent=2))
    
    return resp.json()


def main():
    # Keycloak config
    kc_url = os.getenv("KC_URL", "https://keycloak.ronstad.se")
    realm = os.getenv("KC_REALM", "BB")
    client_id = os.getenv("KC_CLIENT_ID", "pubic-user")
    client_secret = os.getenv("KC_CLIENT_SECRET", "efYsbdlGLYesugyBIKpYayiKYloYgVaX")
    username = os.getenv("KC_USERNAME", "1212")
    password = os.getenv("KC_PASSWORD", "123")
    insecure = os.getenv("KC_INSECURE", "true").lower() == "true"
    
    # API config
    api_url = os.getenv("API_URL", "http://localhost:8080")
    
    print("="*80)
    print("Getting token from Keycloak...")
    print("="*80)
    
    try:
        token = get_token(kc_url, realm, client_id, username, password, client_secret, insecure)
        print(f"✓ Token received (length: {len(token)})")
        print(f"Token: {token[:100]}...")
    except Exception as e:
        print(f"✗ Failed to get token: {e}")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("Testing /auth/jwt endpoint...")
    print("="*80)
    
    try:
        result = test_auth_endpoint(token, api_url, insecure)
        print("\n✓ Request successful!")
    except Exception as e:
        print(f"\n✗ Request failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
