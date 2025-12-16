import sys
from pathlib import Path

# Adding parent directory (payment_service) to the path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
from uuid import UUID
from postgrest.exceptions import APIError
from main import app
from app.database import get_supabase
from app.auth import require_auth


@pytest.fixture
def mock_auth():
    """Mock authentication for tests"""

    def mock_auth_dependency():
        return {
            "sub": "test-user-id",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "realm_access": {"roles": ["user"]},
        }

    app.dependency_overrides[require_auth] = mock_auth_dependency
    yield mock_auth_dependency
    app.dependency_overrides.clear()


@pytest.fixture
def client(mock_supabase, mock_auth):
    """Provide a test client for the FastAPI app with mocked Supabase and auth."""
    # Override the get_supabase dependency with our mock
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_supabase():
    """Provide a mock Supabase client with database table mocks."""
    client = Mock()
    client.rpc = Mock(return_value=Mock())
    return client


@pytest.fixture
def mock_user_data():
    """Provide mock user data from the Users table.

    Schema:
    - card_id: bigint (number)
    - name: text (string)
    - balance: bigint (number)
    - active: boolean
    """
    return {"card_id": 12345, "name": "John Doe", "balance": 500, "active": True}


@pytest.fixture
def mock_item_data():
    """Provide mock item data from the Items table.

    Schema:
    - id: uuid (string)
    - name: text (string)
    - price: bigint (number)
    - barcode_id: bigint (number)
    - active: boolean
    """
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Premium Item",
        "price": 50,
        "barcode_id": 987654321,
        "active": True,
    }


@pytest.fixture
def mock_transaction_data():
    """Provide mock transaction data from the Transactions_history table.

    Schema:
    - id: uuid (string)
    - user_id: bigint (number)
    - item: uuid (string)
    - created_at: timestamp with time zone (string)
    - amount_delta: bigint (number)
    """
    return {
        "id": "660f9500-f30c-52e5-b827-557766551111",
        "user_id": 12345,
        "item": "550e8400-e29b-41d4-a716-446655440000",
        "created_at": "2025-11-26T10:00:00Z",
        "amount_delta": 50,
    }


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check_returns_healthy_status(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestDebitPayment:

    def test_successful_payment(
        self,
        client,
        mock_supabase,
        mock_user_data,
        mock_item_data,
        mock_transaction_data,
    ):
        """Test a successful payment transaction.

        Verifies that:
        - User exists and is active (Users table: active=true)
        - User has sufficient balance (Users table: balance)
        - Item exists and is active (Items table: active=true)
        - Item has correct price (Items table: price)
        - Transaction is recorded with amount_delta (Transactions_history table)
        - New balance is correctly returned
        """
        user_id = mock_user_data["card_id"]
        item_id = UUID(mock_item_data["id"])
        item_price = mock_item_data["price"]
        starting_balance = mock_user_data["balance"]
        new_balance = starting_balance - item_price

        # Mock the RPC call to debit_user function
        mock_supabase.rpc.return_value.execute.return_value.data = str(new_balance)

        response = client.post(
            "/payments/debit", json={"user_id": user_id, "item_id": str(item_id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["new_balance"] == new_balance
        assert data["new_balance"] == (starting_balance - item_price)

        # Verify the RPC was called with correct parameters
        mock_supabase.rpc.assert_called_once_with(
            "debit_user",
            {
                "user_id_input": user_id,
                "item_input": str(item_id),
            },
        )

    # ========= Error Handling Tests =========

    def test_insufficient_funds_error(self, client, mock_supabase, mock_user_data):
        """Test that insufficient funds error returns 402 status code.

        Scenario:
        - User (Users table) exists but balance is less than item price
        - User tries to purchase an item that costs more than their current balance
        - Expected: 402 Insufficient Funds
        """
        user_id = mock_user_data["card_id"]
        item_id = UUID("550e8400-e29b-41d4-a716-446655440000")

        api_error = APIError({"message": "Insufficient funds. Has: 100, Needs: 200"})
        mock_supabase.rpc.return_value.execute.side_effect = api_error

        response = client.post(
            "/payments/debit", json={"user_id": user_id, "item_id": str(item_id)}
        )

        assert response.status_code == 402
        assert response.json()["detail"] == "Insufficient funds"

    def test_user_not_active_error(self, client, mock_supabase, mock_user_data):
        """Test that user not active error returns 403 status code.

        Scenario:
        - User (Users table) exists but active=false
        - User cannot perform transactions
        - Expected: 403 User Not Active
        """
        user_id = mock_user_data["card_id"]
        item_id = UUID("550e8400-e29b-41d4-a716-446655440000")

        api_error = APIError({"message": "User is not active"})
        mock_supabase.rpc.return_value.execute.side_effect = api_error

        response = client.post(
            "/payments/debit", json={"user_id": user_id, "item_id": str(item_id)}
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "User is not active"

    def test_user_not_found_error(self, client, mock_supabase):
        """Test that user not found error returns 404 status code.

        Scenario:
        - Request with a card_id that doesn't exist in Users table
        - Expected: 404 User Not Found
        """
        user_id = 99999
        item_id = UUID("550e8400-e29b-41d4-a716-446655440000")

        api_error = APIError({"message": "User not found"})
        mock_supabase.rpc.return_value.execute.side_effect = api_error

        response = client.post(
            "/payments/debit", json={"user_id": user_id, "item_id": str(item_id)}
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_database_error(self, client, mock_supabase):
        """Test that generic database errors return 500 status code.

        Verifies proper error handling for unexpected database connection
        or query errors.
        """
        user_id = 1
        item_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        error_message = "Connection timeout"

        api_error = APIError({"message": error_message})
        mock_supabase.rpc.return_value.execute.side_effect = api_error

        response = client.post(
            "/payments/debit", json={"user_id": user_id, "item_id": str(item_id)}
        )

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]

    def test_response_model_validation(self, client, mock_supabase):
        """Test that the response model is properly validated.

        Verifies that PaymentResponse includes all required fields with correct types.
        """
        user_id = 1
        item_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        new_balance = 999

        mock_supabase.rpc.return_value.execute.return_value.data = str(new_balance)

        response = client.post(
            "/payments/debit", json={"user_id": user_id, "item_id": str(item_id)}
        )

        assert response.status_code == 200
        # Validate response matches PaymentResponse schema
        data = response.json()
        assert isinstance(data["user_id"], int)
        assert isinstance(data["new_balance"], int)
        assert data["user_id"] == user_id
        assert data["new_balance"] == new_balance
