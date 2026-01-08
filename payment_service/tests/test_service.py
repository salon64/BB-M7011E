import logging
import sys
from pathlib import Path

# Adding parent directory (payment_service) to the path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Add repo root for common

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
from uuid import UUID, uuid4
from postgrest.exceptions import APIError
from main import app
from common.database import get_supabase
from common.auth import require_auth
from payment_service import main


@pytest.fixture
def mock_auth():
    """Mock authentication for tests"""

    def mock_auth_dependency():
        return {
            "sub": "test-user-id",
            "preferred_username": "12345",  # card_id matching test data
            "email": "test@example.com",
            "realm_access": {
                "roles": ["user", "bb_admin"]
            },  # Add bb_admin role for tests
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

    # ======= Authorization User =======

    def test_unauthorized_debit_attempt(self, mock_supabase, caplog):
        """Unauthorized debit attempt should return 403 and log a WARNING."""
        # set auth to a caller that is NOT admin and has different preferred_username
        app.dependency_overrides[require_auth] = lambda: {
            "preferred_username": "1234",
            "realm_access": {"roles": []},
        }
        # supabase mock
        app.dependency_overrides[get_supabase] = lambda: mock_supabase

        client = TestClient(app)
        caplog.set_level(logging.WARNING)

        resp = client.post(
            "/payments/debit",
            json={"user_id": 9999, "item_id": str(uuid4())},
        )

        assert resp.status_code == 403
        assert any(
            "Unauthorized debit attempt" in rec.getMessage() and rec.levelno == logging.WARNING
            for rec in caplog.records
        )

        app.dependency_overrides.clear()
    

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

    def test_unexpected_error_logs_and_500(self, caplog):
        """If the RPC raises, the endpoint should log CRITICAL and return 500."""
        # auth returns matching user id so authorization passes
        app.dependency_overrides[require_auth] = lambda: {
            "preferred_username": "1",
            "realm_access": {"roles": []},
        }

        class FakeRPC:
            def execute(self):
                raise RuntimeError("boom")

        class FakeSupabase:
            def rpc(self, *args, **kwargs):
                return FakeRPC()

        app.dependency_overrides[get_supabase] = lambda: FakeSupabase()

        client = TestClient(app)
        caplog.set_level(logging.CRITICAL)

        resp = client.post(
            "/payments/debit",
            json={"user_id": 1, "item_id": str(uuid4())},
        )

        assert resp.status_code == 500
        assert any(
            "Unexpected error during debit" in rec.getMessage() and rec.levelno == logging.CRITICAL
            for rec in caplog.records
        )

        app.dependency_overrides.clear()

    # ========== Lifespan status testing =========

    def test_lifespan_success(self, monkeypatch, caplog):
        class FakeClient:
            def table(self, *args, **kwargs):
                class Q:
                    def select(self, *a, **k): return self
                    def limit(self, *a, **k): return self
                    def execute(self): return type("R", (), {"data": [1]})()
                return Q()

        monkeypatch.setattr(main, "get_supabase_client", lambda: FakeClient())
        caplog.set_level(logging.INFO)

        with TestClient(main.app) as client:
            r = client.get("/health")
            assert r.status_code == 200
            assert r.json() == {"status": "healthy"}

        assert "Supabase connection established successfully" in caplog.text

    def test_lifespan_failure(self, monkeypatch, caplog):
        monkeypatch.setattr(main, "get_supabase_client", lambda: (_ for _ in ()).throw(RuntimeError("no db")))
        caplog.set_level(logging.ERROR)

        with TestClient(main.app) as client:
            r = client.get("/health")
            assert r.status_code == 200

        assert "Supabase connection failed" in caplog.text or "✗ Supabase connection failed" in caplog.text


class TestTransactionHistory:

    def test_get_transaction_history_db_error(self):
        # APIError during query should return 500
        app.dependency_overrides[require_auth] = lambda: {
            "preferred_username": "admin",
            "realm_access": {"roles": ["bb_admin"]},
        }

        class BadQuery:
            def select(self, *a, **k):
                return self

            def execute(self):
                raise APIError({"message": "DB down"})

        class BadSupabase:
            def table(self, name):
                return BadQuery()

        app.dependency_overrides[get_supabase] = lambda: BadSupabase()

        client = TestClient(app)
        resp = client.get("/transactions/history")
        assert resp.status_code == 500
        assert "Database error" in resp.json()["detail"]

        app.dependency_overrides.clear()

    def test_get_transaction_history_unexpected_error(self):
        # unexpected exception should return 500
        app.dependency_overrides[require_auth] = lambda: {
            "preferred_username": "admin",
            "realm_access": {"roles": ["bb_admin"]},
        }

        class CrashQuery:
            def select(self, *a, **k):
                return self

            def execute(self):
                raise RuntimeError("boom")

        class CrashSupabase:
            def table(self, name):
                return CrashQuery()

        app.dependency_overrides[get_supabase] = lambda: CrashSupabase()

        client = TestClient(app)
        resp = client.get("/transactions/history")
        assert resp.status_code == 500

        app.dependency_overrides.clear()


    def test_get_transaction_by_id_unexpected_error(self):
        tx_id = "660f9500-f30c-52e5-b827-557766551111"
        app.dependency_overrides[require_auth] = lambda: {
            "preferred_username": "12345",
            "realm_access": {"roles": []},
        }

        class CrashQuery:
            def select(self, *a, **k):
                return self

            def eq(self, *a, **k):
                return self

            def execute(self):
                raise RuntimeError("boom")

        class CrashSupabase:
            def table(self, name):
                return CrashQuery()

        app.dependency_overrides[get_supabase] = lambda: CrashSupabase()

        client = TestClient(app)
        resp = client.get(f"/transactions/history/{tx_id}")
        assert resp.status_code == 500

        app.dependency_overrides.clear()