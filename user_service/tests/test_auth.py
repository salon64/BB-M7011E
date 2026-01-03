import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Add repo root for common
import pytest
import jwt as pyjwt
from fastapi import HTTPException
import common.auth as auth_module
from main import app
from fastapi.testclient import TestClient
from app.database import get_supabase
from common.auth import require_auth
from unittest.mock import Mock, patch
from jwt.exceptions import PyJWKClientConnectionError


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
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_supabase():
    """Provide a mock Supabase client with database table mocks."""
    client = Mock()
    client.rpc = Mock(return_value=Mock())
    return client


class TestAuthUtils:
    def test_get_jwks_client_connection_error(self, monkeypatch):
        """Test get_jwks_client() raises HTTPException 503 on connection error."""
        # Reset the global jwks_client to None to force new client creation
        auth_module.jwks_client = None
        
        def fake_pyjwkclient(*args, **kwargs):
            raise Exception("Connection failed")
        
        # Patch PyJWKClient in the auth module
        monkeypatch.setattr(auth_module, "PyJWKClient", fake_pyjwkclient)
        
        with pytest.raises(HTTPException) as exc:
            auth_module.get_jwks_client()
        assert exc.value.status_code == 503
        assert "Failed to create JWKS client" in str(exc.value.detail)

    def test_verify_jwt_token_expired(self, monkeypatch):
        """Test verify_jwt_token raises 401 on ExpiredSignatureError."""
        mock_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "test-key"
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        
        monkeypatch.setattr(auth_module, "get_jwks_client", lambda: mock_client)

        def fake_decode(*a, **k):
            raise pyjwt.ExpiredSignatureError()

        monkeypatch.setattr(pyjwt, "decode", fake_decode)
        
        with pytest.raises(HTTPException) as exc:
            auth_module.verify_jwt_token("token")
        assert exc.value.status_code == 401
        assert "Token expired" in str(exc.value.detail)

    def test_verify_jwt_token_invalid(self, monkeypatch):
        """Test verify_jwt_token raises 401 on InvalidTokenError."""
        mock_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "test-key"
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        
        monkeypatch.setattr(auth_module, "get_jwks_client", lambda: mock_client)

        def fake_decode(*a, **k):
            raise pyjwt.InvalidTokenError()

        monkeypatch.setattr(pyjwt, "decode", fake_decode)
        
        with pytest.raises(HTTPException) as exc:
            auth_module.verify_jwt_token("token")
        assert exc.value.status_code == 401
        assert "Invalid token" in str(exc.value.detail)

    def test_verify_jwt_token_generic_exception(self, monkeypatch):
        """Test verify_jwt_token raises 503 on generic exception."""
        mock_client = Mock()
        mock_client.get_signing_key_from_jwt.side_effect = Exception("Unknown error")
        
        monkeypatch.setattr(auth_module, "get_jwks_client", lambda: mock_client)
        
        with pytest.raises(HTTPException) as exc:
            auth_module.verify_jwt_token("token")
        assert exc.value.status_code == 503
        assert "Unexpected error verifying token" in str(exc.value.detail)

    def test_require_admin_no_admin_role(self, monkeypatch):
        """Test require_admin raises 403 if 'admin' not in roles."""
        monkeypatch.setattr(
            auth_module,
            "verify_jwt_token",
            lambda x: {"realm_access": {"roles": ["user"]}},
        )

        class DummyCred:
            credentials = "token"

        with pytest.raises(HTTPException) as exc:
            auth_module.require_admin(DummyCred())
        assert exc.value.status_code == 403
        assert "Admin access required" in str(exc.value.detail)

    def test_verify_jwt_token_success(self, monkeypatch):
        """Test verify_jwt_token successfully decodes valid token."""
        mock_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "test-key"
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        
        expected_payload = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "realm_access": {"roles": ["user"]}
        }
        
        monkeypatch.setattr(auth_module, "get_jwks_client", lambda: mock_client)
        monkeypatch.setattr(pyjwt, "decode", lambda *a, **k: expected_payload)
        
        result = auth_module.verify_jwt_token("valid-token")
        assert result == expected_payload


#class TestAuthMeEndpoint:
    #def test_me_with_valid_jwt(self, client):
    #    """Test /auth/me returns user info with valid JWT (mocked)."""
    #    response = client.get("/auth/me")
    #    assert response.status_code == 200
    #    data = response.json()
    #    assert data["user_id"] == "test-user-id"
    #    assert data["username"] == "testuser"
    #    assert data["email"] == "test@example.com"
    #    assert "user" in data["roles"]
    #    assert data["service"] == "user-service"

    #def test_me_with_missing_jwt(self, mock_supabase):
    #    """Test /auth/me returns 401 if JWT is missing (no dependency override)."""
    #    app.dependency_overrides.clear()  # Remove auth override
    #    client = TestClient(app)
    #    response = client.get("/auth/me")
    #    assert response.status_code in (401, 403)
