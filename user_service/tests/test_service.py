import sys
from pathlib import Path

# Adding parent directory (user_service) to the path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Add repo root for common

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from postgrest.exceptions import APIError
from main import app
from app.database import get_supabase
from common.auth import require_auth


@pytest.fixture
def mock_auth():
    """Mock authentication for tests"""

    def mock_auth_dependency():
        return {
            "sub": "test-user-id",
            "preferred_username": "12345",  # card_id matching test data
            "email": "test@example.com",
            "realm_access": {"roles": ["user", "bb_admin"]},  # Add admin role for tests
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
    client.table = Mock(return_value=Mock())
    return client


@pytest.fixture
def mock_user_data():
    """Provide mock user data from the Users table."""
    return {
        "card_id": 12345,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "balance": 500,
        "active": True,
    }


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check_returns_healthy_status(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestAuthJWT:
    """Tests for the /auth/jwt endpoint."""

    def test_auth_jwt_returns_decoded_token(self, client, mock_auth):
        """Test that /auth/jwt returns the decoded JWT payload."""
        response = client.get("/auth/jwt")

        assert response.status_code == 200
        data = response.json()
        
        # Verify the mock auth data is returned
        assert data["sub"] == "test-user-id"
        assert data["preferred_username"] == "12345"  # card_id
        assert data["email"] == "test@example.com"
        assert "user" in data["realm_access"]["roles"]
        assert "bb_admin" in data["realm_access"]["roles"]

    def test_auth_jwt_without_token_returns_401(self, mock_supabase):
        """Test that /auth/jwt returns 401 when no token is provided."""
        # Create client without auth override
        app.dependency_overrides.clear()
        app.dependency_overrides[get_supabase] = lambda: mock_supabase
        client = TestClient(app)
        
        response = client.get("/auth/jwt")
        
        assert response.status_code == 401


class TestCreateUser:
    """Tests for the create user endpoint."""

    @patch("app.routes.KeycloakAdmin")
    def test_successful_user_creation(self, mock_keycloak_admin, client, mock_supabase):
        """Test successful user creation in both Supabase and Keycloak.

        Verifies that:
        - Supabase RPC create_user is called with correct parameters
        - Keycloak user is created successfully
        - Response includes both db and keycloak results
        """
        # Mock Supabase response
        mock_supabase.rpc.return_value.execute.return_value = Mock(
            data={"status": "success"}
        )

        # Mock Keycloak admin
        mock_kc_instance = Mock()
        mock_kc_instance.create_user.return_value = "test-keycloak-user-id"
        mock_keycloak_admin.return_value = mock_kc_instance

        response = client.post(
            "/users",
            json={
                "card_id": 12345,
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["db"]["status"] == "success"
        assert data["keycloak"]["status"] == "created"
        assert data["keycloak"]["user_id"] == "test-keycloak-user-id"

        # Verify Supabase RPC was called
        mock_supabase.rpc.assert_called_once_with(
            "create_user",
            {
                "card_id_input": 12345,
                "first_name_input": "John",
                "last_name_input": "Doe",
            },
        )

    def test_supabase_error_during_user_creation(self, client, mock_supabase):
        """Test that Supabase errors are properly handled during user creation."""
        # Mock Supabase error
        mock_supabase.rpc.return_value.execute.side_effect = Exception(
            "Database connection error"
        )

        response = client.post(
            "/users",
            json={
                "card_id": 12345,
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 500
        assert "Supabase error" in response.json()["detail"]



class TestAddBalance:
    """Tests for the add balance endpoint."""

    def test_successful_balance_addition(self, client, mock_supabase):
        """Test successful balance addition to a user account.

        Verifies that:
        - User exists
        - Balance is correctly added
        - New balance is returned
        """
        card_id = 12345
        amount = 100
        new_balance = 600

        # Mock the RPC call to add_balance function
        mock_supabase.rpc.return_value.execute.return_value.data = new_balance

        response = client.post(
            "/user/add_balance",
            params={"user_id": "test-user", "amount": amount},
            json={"card_id": card_id, "amount": amount},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id_input"] == card_id
        assert data["new_balance"] == new_balance

        # Verify the RPC was called with correct parameters
        mock_supabase.rpc.assert_called_once_with(
            "add_balance",
            {
                "user_id_input": card_id,
                "balance_input": amount,
            },
        )

    def test_user_not_found_error(self, client, mock_supabase):
        """Test that user not found error returns 404 status code.

        Scenario:
        - Request with a card_id that doesn't exist in Users table
        - Expected: 404 User Not Found
        """
        card_id = 99999
        amount = 100

        api_error = APIError({"message": "User not found"})
        mock_supabase.rpc.return_value.execute.side_effect = api_error

        response = client.post(
            "/user/add_balance",
            params={"user_id": "test-user", "amount": amount},
            json={"card_id": card_id, "amount": amount},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_database_error(self, client, mock_supabase):
        """Test that generic database errors return 500 status code."""
        card_id = 12345
        amount = 100
        error_message = "Connection timeout"

        api_error = APIError({"message": error_message})
        mock_supabase.rpc.return_value.execute.side_effect = api_error

        response = client.post(
            "/user/add_balance",
            params={"user_id": "test-user", "amount": amount},
            json={"card_id": card_id, "amount": amount},
        )

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]


class TestSetUserStatus:
    """Tests for the set user status endpoint."""

    def test_successful_status_activation(self, client, mock_supabase):
        """Test successful user status activation.

        Verifies that:
        - User status is updated to active
        - Response contains confirmation message
        """
        user_id = 12345

        # Mock the RPC call to user_status function
        mock_supabase.rpc.return_value.execute.return_value.data = (
            "User status updated successfully"
        )

        response = client.post(
            "/user/set_status",
            json={"user_id_input": str(user_id), "user_status_input": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "User status updated successfully"

        # Verify the RPC was called with correct parameters
        mock_supabase.rpc.assert_called_once_with(
            "user_status",
            {
                "user_id_input": str(user_id),
                "user_status_input": True,
            },
        )

    def test_successful_status_deactivation(self, client, mock_supabase):
        """Test successful user status deactivation."""
        user_id = 12345

        # Mock the RPC call to user_status function
        mock_supabase.rpc.return_value.execute.return_value.data = (
            "User status updated successfully"
        )

        response = client.post(
            "/user/set_status",
            json={"user_id_input": str(user_id), "user_status_input": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "User status updated successfully"

    def test_user_not_found_error(self, client, mock_supabase):
        """Test that user not found error returns 404 status code."""
        user_id = 99999

        api_error = APIError({"message": "User not found"})
        mock_supabase.rpc.return_value.execute.side_effect = api_error

        response = client.post(
            "/user/set_status",
            json={"user_id_input": str(user_id), "user_status_input": True},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_already_active_error(self, client, mock_supabase):
        """Test that trying to activate an already active user returns 400."""
        user_id = 12345

        api_error = APIError({"message": "User status is already active=TRUE"})
        mock_supabase.rpc.return_value.execute.side_effect = api_error

        response = client.post(
            "/user/set_status",
            json={"user_id_input": str(user_id), "user_status_input": True},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "User status is already active=TRUE"

    def test_already_inactive_error(self, client, mock_supabase):
        """Test that trying to deactivate an already inactive user returns 400."""
        user_id = 12345

        api_error = APIError({"message": "User status is already active=FALSE"})
        mock_supabase.rpc.return_value.execute.side_effect = api_error

        response = client.post(
            "/user/set_status",
            json={"user_id_input": str(user_id), "user_status_input": False},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "User status is already active=FALSE"


class TestFetchUserInfo:
    """Tests for the fetch user info endpoint."""

    def test_successful_user_info_fetch(self, client, mock_supabase, mock_user_data):
        """Test successful retrieval of user information.

        Verifies that:
        - User exists in database
        - User information is correctly returned
        - Response includes name, email, balance, and status
        """
        user_id = mock_user_data["card_id"]

        # Mock the RPC call to fetch_user_info function
        mock_supabase.rpc.return_value.execute.return_value.data = {
            "first_name": mock_user_data["first_name"],
            "last_name": mock_user_data["last_name"],
            "balance": mock_user_data["balance"],
            "active": mock_user_data["active"],
        }

        response = client.post(
            "/user/fetch_info",
            json={"user_id": user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == mock_user_data["first_name"]
        assert data["last_name"] == mock_user_data["last_name"]
        assert data["balance"] == mock_user_data["balance"]
        assert data["active"] == mock_user_data["active"]

        # Verify the RPC was called with correct parameters
        mock_supabase.rpc.assert_called_once_with(
            "fetch_user_info",
            {
                "user_id_input": user_id,
            },
        )

    def test_user_not_found_error(self, client, mock_supabase):
        """Test that user not found error returns 404 status code.

        Scenario:
        - Request with a user_id that doesn't exist in Users table
        - Expected: 404 User Not Found
        """
        user_id = 99999

        api_error = APIError({"message": "User not found"})
        mock_supabase.rpc.return_value.execute.side_effect = api_error

        response = client.post(
            "/user/fetch_info",
            json={"user_id": user_id},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_database_error(self, client, mock_supabase):
        """Test that generic database errors return 500 status code."""
        user_id = 12345
        error_message = "Connection timeout"

        api_error = APIError({"message": error_message})
        mock_supabase.rpc.return_value.execute.side_effect = api_error

        response = client.post(
            "/user/fetch_info",
            json={"user_id": user_id},
        )

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]

    def test_response_model_validation(self, client, mock_supabase):
        """Test that the response model is properly validated.

        Verifies that the response includes all required fields with correct types.
        """
        user_id = 12345

        mock_supabase.rpc.return_value.execute.return_value.data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "balance": 750,
            "active": True,
        }

        response = client.post(
            "/user/fetch_info",
            json={"user_id": user_id},
        )

        assert response.status_code == 200
        # Validate response structure
        data = response.json()
        assert isinstance(data["first_name"], str)
        assert isinstance(data["last_name"], str)
        assert isinstance(data["balance"], int)
        assert isinstance(data["active"], bool)
        assert data["first_name"] == "Jane"
        assert data["last_name"] == "Doe"
        assert data["balance"] == 750
        assert data["active"] is True
