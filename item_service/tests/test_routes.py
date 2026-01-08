import sys
from pathlib import Path

# Adding parent directory (item_service) to the path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Add repo root for common

# Imports after path setup
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

from main import app
from common.database import get_supabase
from common.auth import require_auth


@pytest.fixture
def mock_auth_admin():
    """Mock authentication for admin users"""

    def mock_auth_dependency():
        return {
            "sub": "test-admin-id",
            "preferred_username": "admin_user",
            "email": "admin@example.com",
            "realm_access": {"roles": ["user", "bb_admin"]},
        }

    app.dependency_overrides[require_auth] = mock_auth_dependency
    yield mock_auth_dependency
    app.dependency_overrides.clear()


@pytest.fixture
def mock_auth_user():
    """Mock authentication for regular users (non-admin)"""

    def mock_auth_dependency():
        return {
            "sub": "test-user-id",
            "preferred_username": "regular_user",
            "email": "user@example.com",
            "realm_access": {"roles": ["user"]},
        }

    app.dependency_overrides[require_auth] = mock_auth_dependency
    yield mock_auth_dependency
    app.dependency_overrides.clear()


@pytest.fixture
def mock_supabase():
    """Provide a mock Supabase client with database table mocks."""
    client = Mock()
    client.table = Mock(return_value=Mock())
    return client


@pytest.fixture
def client_admin(mock_supabase, mock_auth_admin):
    """Provide a test client for the FastAPI app with admin auth."""
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_user(mock_supabase, mock_auth_user):
    """Provide a test client for the FastAPI app with regular user auth."""
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_item_data():
    """Provide mock item data from the Items table."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Test Item",
        "price": 100,
        "barcode_id": 12345,
        "active": True,
    }


@pytest.fixture
def mock_inactive_item_data():
    """Provide mock inactive item data."""
    return {
        "id": "660f9500-f30c-52e5-b827-557766551111",
        "name": "Inactive Item",
        "price": 50,
        "barcode_id": 67890,
        "active": False,
    }


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check_returns_healthy_status(self, client_admin):
        response = client_admin.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestCreateItem:
    """Tests for the create item endpoint."""

    def test_create_item_success(self, client_admin, mock_supabase, mock_item_data):
        """Test successful item creation by admin."""
        mock_table = Mock()
        mock_insert = Mock()
        mock_execute = Mock()
        mock_execute.data = [mock_item_data]

        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = mock_execute

        response = client_admin.post(
            "/items",
            json={
                "name": "Test Item",
                "price": 100,
                "barcode_id": 12345,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["name"] == "Test Item"
        assert data["price"] == 100

    def test_create_item_forbidden_for_non_admin(
        self, client_user, mock_supabase, mock_item_data
    ):
        """Test that non-admin users cannot create items."""
        response = client_user.post(
            "/items",
            json={
                "name": "Test Item",
                "price": 100,
                "barcode_id": 12345,
            },
        )

        assert response.status_code == 403
        assert "BB Admin privileges required" in response.json()["detail"]

    def test_create_item_without_barcode(self, client_admin, mock_supabase):
        """Test creating item without optional barcode_id."""
        item_data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "No Barcode Item",
            "price": 50,
            "barcode_id": None,
            "active": True,
        }

        mock_table = Mock()
        mock_insert = Mock()
        mock_execute = Mock()
        mock_execute.data = [item_data]

        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = mock_execute

        response = client_admin.post(
            "/items",
            json={
                "name": "No Barcode Item",
                "price": 50,
            },
        )

        assert response.status_code == 200


class TestFetchItemInfo:
    """Tests for the fetch item info endpoint."""

    def test_fetch_item_info_success(self, client_admin, mock_supabase, mock_item_data):
        """Test successful item fetch by ID."""
        mock_table = Mock()
        mock_select = Mock()
        mock_eq = Mock()
        mock_execute = Mock()
        mock_execute.data = [mock_item_data]

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = mock_execute

        response = client_admin.post(
            "/items/fetch_info",
            json={"item_id": mock_item_data["id"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Item"
        assert data["price"] == 100
        assert data["active"] is True

    def test_fetch_item_info_not_found(self, client_admin, mock_supabase):
        """Test fetch item returns 404 when item doesn't exist."""
        mock_table = Mock()
        mock_select = Mock()
        mock_eq = Mock()
        mock_execute = Mock()
        mock_execute.data = []

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = mock_execute

        response = client_admin.post(
            "/items/fetch_info",
            json={"item_id": "550e8400-e29b-41d4-a716-446655440000"},
        )

        assert response.status_code == 404
        assert "Item not found" in response.json()["detail"]


class TestFetchItemByBarcode:
    """Tests for the fetch item by barcode endpoint."""

    def test_fetch_by_barcode_success(
        self, client_admin, mock_supabase, mock_item_data
    ):
        """Test successful item fetch by barcode."""
        mock_table = Mock()
        mock_select = Mock()
        mock_eq1 = Mock()
        mock_eq2 = Mock()
        mock_execute = Mock()
        mock_execute.data = [mock_item_data]

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = mock_execute

        response = client_admin.post(
            "/items/fetch_by_barcode",
            json={"barcode_id": 12345},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["barcode_id"] == 12345

    def test_fetch_by_barcode_not_found(self, client_admin, mock_supabase):
        """Test fetch by barcode returns 404 when item doesn't exist."""
        mock_table = Mock()
        mock_select = Mock()
        mock_eq1 = Mock()
        mock_eq2 = Mock()
        mock_execute = Mock()
        mock_execute.data = []

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = mock_execute

        response = client_admin.post(
            "/items/fetch_by_barcode",
            json={"barcode_id": 99999},
        )

        assert response.status_code == 404


class TestListItems:
    """Tests for the list items endpoint."""

    def test_list_items_all(self, client_admin, mock_supabase, mock_item_data):
        """Test listing all items."""
        mock_table = Mock()
        mock_select = Mock()
        mock_execute = Mock()
        mock_execute.data = [mock_item_data]

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.execute.return_value = mock_execute

        response = client_admin.post(
            "/items/list",
            json={"active_only": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["active_only"] is False

    def test_list_items_active_only(self, client_admin, mock_supabase, mock_item_data):
        """Test listing only active items."""
        mock_table = Mock()
        mock_select = Mock()
        mock_eq = Mock()
        mock_execute = Mock()
        mock_execute.data = [mock_item_data]

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = mock_execute

        response = client_admin.post(
            "/items/list",
            json={"active_only": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["active_only"] is True


class TestUpdateItem:
    """Tests for the update item endpoint."""

    def test_update_item_success(self, client_admin, mock_supabase, mock_item_data):
        """Test successful item update by admin."""
        updated_item = mock_item_data.copy()
        updated_item["name"] = "Updated Item"
        updated_item["price"] = 150

        mock_table = Mock()
        mock_update = Mock()
        mock_eq = Mock()
        mock_execute = Mock()
        mock_execute.data = [updated_item]

        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value = mock_eq
        mock_eq.execute.return_value = mock_execute

        response = client_admin.put(
            f"/items/update?item_id={mock_item_data['id']}",
            json={"name": "Updated Item", "price": 150},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["item"]["name"] == "Updated Item"

    def test_update_item_forbidden_for_non_admin(self, client_user, mock_supabase):
        """Test that non-admin users cannot update items."""
        response = client_user.put(
            "/items/update?item_id=550e8400-e29b-41d4-a716-446655440000",
            json={"name": "Updated Item"},
        )

        assert response.status_code == 403

    def test_update_item_no_fields(self, client_admin, mock_supabase):
        """Test update with no fields returns 400."""
        response = client_admin.put(
            "/items/update?item_id=550e8400-e29b-41d4-a716-446655440000",
            json={},
        )

        assert response.status_code == 400
        assert "No fields to update" in response.json()["detail"]


class TestSetItemStatus:
    """Tests for the set item status endpoint."""

    def test_set_status_success(self, client_admin, mock_supabase, mock_item_data):
        """Test successful status change."""
        mock_table = Mock()
        mock_select = Mock()
        mock_update = Mock()
        mock_eq_select = Mock()
        mock_eq_update = Mock()
        mock_execute_select = Mock()
        mock_execute_update = Mock()

        mock_execute_select.data = [{"active": True}]
        mock_execute_update.data = [{"active": False}]

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq_select
        mock_eq_select.execute.return_value = mock_execute_select

        mock_table.update.return_value = mock_update
        mock_update.eq.return_value = mock_eq_update
        mock_eq_update.execute.return_value = mock_execute_update

        response = client_admin.post(
            "/items/set_status",
            json={
                "item_id": mock_item_data["id"],
                "item_status": False,
            },
        )

        assert response.status_code == 200

    def test_set_status_already_same(self, client_admin, mock_supabase, mock_item_data):
        """Test setting status to same value returns 400."""
        mock_table = Mock()
        mock_select = Mock()
        mock_eq = Mock()
        mock_execute = Mock()
        mock_execute.data = [{"active": True}]

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = mock_execute

        response = client_admin.post(
            "/items/set_status",
            json={
                "item_id": mock_item_data["id"],
                "item_status": True,
            },
        )

        assert response.status_code == 400
        assert "already active" in response.json()["detail"]

    def test_set_status_forbidden_for_non_admin(self, client_user, mock_supabase):
        """Test that non-admin users cannot set item status."""
        response = client_user.post(
            "/items/set_status",
            json={
                "item_id": "550e8400-e29b-41d4-a716-446655440000",
                "item_status": False,
            },
        )

        assert response.status_code == 403


class TestDeleteItem:
    """Tests for the delete item endpoint."""

    def test_delete_item_success(self, client_admin, mock_supabase, mock_item_data):
        """Test successful item deletion (soft delete)."""
        deleted_item = mock_item_data.copy()
        deleted_item["active"] = False

        mock_table = Mock()
        mock_update = Mock()
        mock_eq = Mock()
        mock_execute = Mock()
        mock_execute.data = [deleted_item]

        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value = mock_eq
        mock_eq.execute.return_value = mock_execute

        response = client_admin.request(
            "DELETE",
            "/items/delete",
            json={"item_id": mock_item_data["id"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "deleted" in data["message"].lower()

    def test_delete_item_not_found(self, client_admin, mock_supabase):
        """Test delete returns 404 when item doesn't exist."""
        mock_table = Mock()
        mock_update = Mock()
        mock_eq = Mock()
        mock_execute = Mock()
        mock_execute.data = []

        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value = mock_eq
        mock_eq.execute.return_value = mock_execute

        response = client_admin.request(
            "DELETE",
            "/items/delete",
            json={"item_id": "550e8400-e29b-41d4-a716-446655440000"},
        )

        assert response.status_code == 404

    def test_delete_item_forbidden_for_non_admin(self, client_user, mock_supabase):
        """Test that non-admin users cannot delete items."""
        response = client_user.request(
            "DELETE",
            "/items/delete",
            json={"item_id": "550e8400-e29b-41d4-a716-446655440000"},
        )

        assert response.status_code == 403


class TestDecodedJWT:
    """Tests for the JWT endpoint."""

    def test_get_decoded_jwt(self, client_admin):
        """Test that decoded JWT returns token data."""
        response = client_admin.get("/auth/jwt")

        assert response.status_code == 200
        data = response.json()
        assert "sub" in data
        assert "realm_access" in data
