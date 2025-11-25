import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app

@pytest.fixture
def client():
    """A pytest fixture that provides a TestClient instance for the app."""
    with TestClient(app) as c:
        yield c

class TestRoutes:

    def test_health_check(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    @patch('app.routes.get_supabase')
    def test_debit_payment_success(self, mock_get_supabase, client):
        """Test a successful debit payment by mocking the Supabase RPC call."""
        # Configure the mock to simulate a successful RPC call returning a new balance.
        mock_get_supabase.return_value.rpc.return_value.execute.return_value.data = 50.0

        payment_data = {"user_id": "some-user-id", "amount": 100.0}

        response = client.post("/payments/debit", json=payment_data)

        assert response.status_code == 200
        assert response.json() == {"user_id": "some-user-id", "new_balance": 50.0}
        mock_get_supabase.return_value.rpc.assert_called_once()

    @patch('app.routes.get_supabase')
    def test_debit_payment_insufficient_funds(self, mock_get_supabase, client):
        """Test debit payment with insufficient funds."""
        # Configure the mock to simulate the database raising an error for insufficient funds.
        from postgrest.exceptions import APIError
        mock_get_supabase.return_value.rpc.return_value.execute.side_effect = APIError(message="insufficient funds")

        payment_data = {"user_id": "some-user-id", "amount": 200.0}

        response = client.post("/payments/debit", json=payment_data)

        assert response.status_code == 402
        assert response.json() == {"detail": "Insufficient funds"}
