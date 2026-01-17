import os
import requests
from locust import HttpUser, task, between, events

# ======================
# CONFIG
# ======================
KC_URL = os.getenv("KC_URL", "https://keycloak.ronstad.se")
KC_REALM = os.getenv("KC_REALM", "BB")

USER_CLIENT_ID = os.getenv("KC_CLIENT_ID", "public-user")
ADMIN_CLIENT_ID = os.getenv("KC_ADMIN_CLIENT_ID", "admin-cli")

USER_USERNAME = os.getenv("KC_USERNAME", "1212")
USER_PASSWORD = os.getenv("KC_PASSWORD", "hej")

ADMIN_USERNAME = os.getenv("KC_ADMIN_USERNAME", "bb-admin")
ADMIN_PASSWORD = os.getenv("KC_ADMIN_PASSWORD", "bb-admin")

INSECURE = True

# Service URLs - update these to match your environment
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "https://payment-service-dev.ronstad.se")
ITEM_SERVICE_URL = os.getenv("ITEM_SERVICE_URL", "https://item-service-dev.ronstad.se")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "https://user-service-dev.ronstad.se")

# ======================
# AUTH
# ======================
def get_token(username, password, client_id):
    try:
        r = requests.post(
            f"{KC_URL}/realms/{KC_REALM}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": client_id,
                "username": username,
                "password": password,
            },
            verify=not INSECURE,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["access_token"]
    except Exception as e:
        print(f"[AUTH ERROR] Failed to get token for {username} with client {client_id}: {e}")
        raise

# ======================
# USER LOAD - Payment Service
# ======================
class PaymentServiceUser(HttpUser):
    host = PAYMENT_SERVICE_URL
    weight = 10
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.token = get_token(USER_USERNAME, USER_PASSWORD, USER_CLIENT_ID)
        self.headers = {"Authorization": f"Bearer {self.token}"}
        # Extract user_id from username (assuming it's numeric)
        try:
            self.user_id = int(USER_USERNAME)
        except ValueError:
            self.user_id = 1

    @task(5)
    def health(self):
        self.client.get("/health")

    @task(5)
    def jwt_info(self):
        self.client.get("/auth/jwt", headers=self.headers)

    @task(6)
    def transactions(self):
        self.client.get("/transactions/history", headers=self.headers)

    @task(3)
    def debit(self):
        # Get item_id from the parent ItemServiceUser if available
        item_id = getattr(self, 'item_id', None)
        if not item_id:
            item_id = "550e8400-e29b-41d4-a716-446655440000"
        
        with self.client.post(
            "/payments/debit",
            headers=self.headers,
            json={"user_id": self.user_id, "item_id": item_id},
            catch_response=True,
        ) as resp:
            # Accept 200 (success) and 404 (item not found)
            if resp.status_code in [200, 404]:
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

# ======================
# USER LOAD - Item Service
# ======================
class ItemServiceUser(HttpUser):
    host = ITEM_SERVICE_URL
    weight = 9
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.token = get_token(USER_USERNAME, USER_PASSWORD, USER_CLIENT_ID)
        self.headers = {"Authorization": f"Bearer {self.token}"}
        # Extract user_id from username (assuming it's numeric)
        try:
            self.user_id = int(USER_USERNAME)
        except ValueError:
            self.user_id = 1
        # Fetch available items on startup
        self.items = []
        try:
            resp = requests.post(
                f"{ITEM_SERVICE_URL}/items/list",
                headers=self.headers,
                json={"active_only": True},
                verify=not INSECURE,
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.items = [item["id"] for item in data.get("items", [])[:10]]
        except Exception as e:
            print(f"[WARNING] Could not fetch items: {e}")

    @task(5)
    def health(self):
        self.client.get("/health")

    @task(10)
    def list_items(self):
        self.client.post("/items/list", headers=self.headers, json={"active_only": True})

    @task(8)
    def fetch_item(self):
        if self.items:
            item_id = self.items[0]  # Use first available item
        else:
            item_id = "550e8400-e29b-41d4-a716-446655440000"  # Fallback UUID
        
        with self.client.post(
            "/items/fetch_info",
            headers=self.headers,
            json={"item_id": item_id},
            catch_response=True,
        ) as resp:
            # Allow 200 (success) and 404 (item not found)
            if resp.status_code in [200, 404]:
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

# ======================
# ADMIN LOAD - Item Service
# ======================
class AdminItemServiceUser(HttpUser):
    host = ITEM_SERVICE_URL
    weight = 1
    wait_time = between(0.2, 1)

    def on_start(self):
        self.token = get_token(ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_CLIENT_ID)
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def create_item(self):
        self.client.post(
            "/items",
            headers=self.headers,
            json={
                "name": "stress-item",
                "price": 10,
                "barcode_id": "STRESS123",
            },
        )

    @task(4)
    def update_item(self):
        self.client.put(
            "/items/update",
            headers=self.headers,
            json={"item_id": 1, "price": 11},
        )

    @task(2)
    def set_status(self):
        self.client.post(
            "/items/set_status",
            headers=self.headers,
            json={"item_id": 1, "active": True},
        )
