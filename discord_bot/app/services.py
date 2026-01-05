# Service clients for communicating with other microservices
import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class ServiceClient:
    """Base client for making HTTP requests to services."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    async def get(self, endpoint: str, headers: dict = None):
        """Make a GET request to the service."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"HTTP error: {e}")
                raise
    
    async def post(self, endpoint: str, data: dict = None, headers: dict = None):
        """Make a POST request to the service."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    json=data,
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"HTTP error: {e}")
                raise


class UserServiceClient(ServiceClient):
    """Client for the User Service."""
    
    def __init__(self):
        super().__init__(settings.user_service_url)
    
    async def get_user_info(self, user_id: str, token: str):
        """Get user information."""
        headers = {"Authorization": f"Bearer {token}"}
        return await self.get(f"/users/{user_id}", headers=headers)
    
    async def get_balance(self, user_id: str, token: str):
        """Get user balance."""
        headers = {"Authorization": f"Bearer {token}"}
        return await self.get(f"/users/{user_id}/balance", headers=headers)


class ItemServiceClient(ServiceClient):
    """Client for the Item Service."""
    
    def __init__(self):
        super().__init__(settings.item_service_url)
    
    async def list_items(self, active_only: bool = True):
        """List available items."""
        endpoint = "/items" if not active_only else "/items?active=true"
        return await self.get(endpoint)
    
    async def get_item(self, item_id: int):
        """Get item by ID."""
        return await self.get(f"/items/{item_id}")


class PaymentServiceClient(ServiceClient):
    """Client for the Payment Service."""
    
    def __init__(self):
        super().__init__(settings.payment_service_url)
    
    async def debit_payment(self, user_id: int, item_id: int, token: str):
        """Process a payment/purchase."""
        headers = {"Authorization": f"Bearer {token}"}
        data = {"user_id": user_id, "item_id": item_id}
        return await self.post("/payments/debit", data=data, headers=headers)


# Service client instances
user_service = UserServiceClient()
item_service = ItemServiceClient()
payment_service = PaymentServiceClient()
