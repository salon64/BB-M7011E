import os
import sys
import requests
import json

# =========================
# CONFIG
# =========================
KC_URL = os.getenv("KC_URL", "https://keycloak.ronstad.se")
KC_REALM = os.getenv("KC_REALM", "BB")
KC_CLIENT_ID = os.getenv("KC_CLIENT_ID", "public-user")
# KC_CLIENT_SECRET = os.getenv("KC_CLIENT_SECRET", "efYsbdlGLYesugyBIKpYayiKYloYgVaX")

KC_USERNAME = os.getenv("KC_USERNAME", "1212")
KC_PASSWORD = os.getenv("KC_PASSWORD", "hej")

API_BASE_URL = os.getenv("API_BASE_URL", "http://payment-service-dev.ronstad.se")
INSECURE = os.getenv("KC_INSECURE", "true").lower() == "true"


# =========================
# AUTH
# =========================
def get_access_token() -> str:
    token_url = f"{KC_URL}/realms/{KC_REALM}/protocol/openid-connect/token"

    data = {
        "grant_type": "password",
        "client_id": KC_CLIENT_ID,
        # "client_secret": KC_CLIENT_SECRET,
        "username": KC_USERNAME,
        "password": KC_PASSWORD,
    }

    r = requests.post(token_url, data=data, verify=not INSECURE, timeout=15)

    if r.status_code != 200:
        print("Token request failed:")
        print(r.text)
        sys.exit(1)

    return r.json()["access_token"]


# =========================
# API CALL
# =========================
def get_transaction_history(
    access_token: str,
    user_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
):
    url = f"{API_BASE_URL}/transactions/history"

    params = {
        "limit": limit,
        "offset": offset,
    }

    if user_id is not None:
        params["user_id"] = user_id

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    r = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=15,
    )

    print("\n" + "=" * 80)
    print(f"GET {r.url}")
    print(f"STATUS: {r.status_code}")
    print("=" * 80)

    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)


# =========================
# MAIN
# =========================
def main():
    token = get_access_token()
    print("✓ Access token acquired")

    # ---- TEST CASES ----

    print("\n### 1. Regular user – own transactions")
    get_transaction_history(token)

    print("\n### 2. Regular user – attempt another user's transactions (should 403)")
    get_transaction_history(token, user_id=9999)

    print("\n### 3. Admin / service account – all transactions")
    get_transaction_history(token)

    print("\n### 4. Admin / service account – specific user")
    get_transaction_history(token, user_id=1)

    print("\n### 5. Pagination test")
    get_transaction_history(token, limit=10, offset=0)
    get_transaction_history(token, limit=10, offset=10)


if __name__ == "__main__":
    main()
