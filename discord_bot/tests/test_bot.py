import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Add repo root for common

import pytest
from unittest.mock import Mock, AsyncMock, patch


class TestBotCommands:
    """Test Discord bot commands."""

    def test_bot_config_loads(self):
        """Test that bot configuration loads correctly."""
        from app.config import settings
        assert settings.command_prefix == "!"

    @pytest.mark.asyncio
    async def test_service_client_get(self):
        """Test ServiceClient GET request."""
        from app.services import ServiceClient
        
        client = ServiceClient("http://test-service")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "ok"}
            mock_response.raise_for_status = Mock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.get("/health")
            assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_service_client_post(self):
        """Test ServiceClient POST request."""
        from app.services import ServiceClient
        
        client = ServiceClient("http://test-service")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status = Mock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.post("/action", data={"key": "value"})
            assert result == {"success": True}


class TestServiceClients:
    """Test individual service clients."""

    def test_user_service_client_init(self):
        """Test UserServiceClient initialization."""
        from app.services import UserServiceClient
        client = UserServiceClient()
        assert "user-service" in client.base_url or "localhost" in client.base_url

    def test_item_service_client_init(self):
        """Test ItemServiceClient initialization."""
        from app.services import ItemServiceClient
        client = ItemServiceClient()
        assert "item-service" in client.base_url or "localhost" in client.base_url

    def test_payment_service_client_init(self):
        """Test PaymentServiceClient initialization."""
        from app.services import PaymentServiceClient
        client = PaymentServiceClient()
        assert "payment-service" in client.base_url or "localhost" in client.base_url
