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

# ======================
# AUTH
# ======================
def get_token(username, password, client_id):
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

# ======================
# USER LOAD
# ======================
class RegularUser(HttpUser):
    weight = 19
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.token = get_token(USER_USERNAME, USER_PASSWORD, USER_CLIENT_ID)
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def health(self):
        self.client.get("/health")

    @task(5)
    def jwt_info(self):
        self.client.get("/auth/jwt", headers=self.headers)

    @task(10)
    def list_items(self):
        self.client.post("/items/list", headers=self.headers, json={"active_only": True})

    @task(8)
    def fetch_item(self):
        self.client.post("/items/fetch_info", headers=self.headers, json={"item_id": 1})

    @task(6)
    def transactions(self):
        self.client.get("/transactions/history", headers=self.headers)

    @task(3)
    def debit(self):
        self.client.post(
            "/payments/debit",
            headers=self.headers,
            json={"amount": 10, "reason": "stress-test"},
        )

# ======================
# ADMIN LOAD
# ======================
class AdminUser(HttpUser):
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
                "barcode": "STRESS123",
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
