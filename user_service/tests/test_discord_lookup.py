import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Add repo root for common

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
from main import app
from common.database import get_supabase
from common.auth import require_auth


@pytest.fixture
def mock_supabase():
    """Provide a mock Supabase client."""
    client = Mock()
    return client


@pytest.fixture
def mock_auth_admin():
    """Mock authentication with bb_admin role."""

    def mock_auth_dependency():
        return {
            "sub": "test-user-id",
            "preferred_username": "12345",
            "email": "admin@example.com",
            "realm_access": {"roles": ["user", "bb_admin"]},
        }

    return mock_auth_dependency


@pytest.fixture
def mock_auth_no_admin():
    """Mock authentication without bb_admin role."""

    def mock_auth_dependency():
        return {
            "sub": "test-user-id",
            "preferred_username": "12345",
            "email": "user@example.com",
            "realm_access": {"roles": ["user"]},
        }

    return mock_auth_dependency


@pytest.fixture
def client_admin(mock_supabase, mock_auth_admin):
    """Test client with admin auth."""
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    app.dependency_overrides[require_auth] = mock_auth_admin
    yield TestClient(app), mock_supabase
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_admin(mock_supabase, mock_auth_no_admin):
    """Test client without admin auth."""
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    app.dependency_overrides[require_auth] = mock_auth_no_admin
    yield TestClient(app), mock_supabase
    app.dependency_overrides.clear()


class TestDiscordLookup:
    def test_discord_lookup_success(self, client_admin):
        """Test successful Discord lookup returns card_id."""
        client, mock_supabase = client_admin

        # Mock the Supabase table query chain
        mock_table = Mock()
        mock_select = Mock()
        mock_eq = Mock()
        mock_execute = Mock()

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = Mock(data=[{"card_id": 67890}])

        response = client.post(
            "/user/discord_lookup", json={"discord_id": "123456789012345678"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["card_id"] == 67890
        assert data["discord_id"] == "123456789012345678"

        # Verify correct table and query were used
        mock_supabase.table.assert_called_once_with("Users")
        mock_table.select.assert_called_once_with("card_id")
        mock_select.eq.assert_called_once_with("discord", "123456789012345678")

    def test_discord_lookup_user_not_found(self, client_admin):
        """Test Discord lookup returns 404 when user not found."""
        client, mock_supabase = client_admin

        # Mock empty result
        mock_table = Mock()
        mock_select = Mock()
        mock_eq = Mock()

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = Mock(data=[])

        response = client.post(
            "/user/discord_lookup", json={"discord_id": "999999999999999999"}
        )

        assert response.status_code == 404
        assert "No user linked with this Discord ID" in response.json()["detail"]

    def test_discord_lookup_requires_admin(self, client_no_admin):
        """Test Discord lookup requires bb_admin role."""
        client, mock_supabase = client_no_admin

        response = client.post(
            "/user/discord_lookup", json={"discord_id": "123456789012345678"}
        )

        assert response.status_code == 403
        assert "BB Admin privileges required" in response.json()["detail"]

    def test_discord_lookup_missing_discord_id(self, client_admin):
        """Test Discord lookup requires discord_id in request."""
        client, mock_supabase = client_admin

        response = client.post("/user/discord_lookup", json={})

        assert response.status_code == 422  # Validation error

    def test_discord_lookup_database_error(self, client_admin):
        """Test Discord lookup handles database errors gracefully."""
        client, mock_supabase = client_admin

        # Mock database exception
        mock_supabase.table.side_effect = Exception("Database connection failed")

        response = client.post(
            "/user/discord_lookup", json={"discord_id": "123456789012345678"}
        )

        assert response.status_code == 500
        assert "unexpected error" in response.json()["detail"].lower()
