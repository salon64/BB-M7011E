import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import pytest
import jwt as pyjwt
from fastapi import HTTPException
from app import auth as auth_module
from main import app
from fastapi.testclient import TestClient
from app.database import get_supabase
from app.auth import require_auth
from unittest.mock import Mock


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
    def test_get_public_keys_request_exception(self, monkeypatch):
        """Test get_public_keys() raises HTTPException 503 on requests error."""
        monkeypatch.setattr(auth_module, "public_keys", None)

        def fake_get(*args, **kwargs):
            raise auth_module.requests.RequestException()

        monkeypatch.setattr(auth_module.requests, "get", fake_get)
        with pytest.raises(HTTPException) as exc:
            auth_module.get_public_keys()
        assert exc.value.status_code == 503
        assert "Authentication service unavailable" in str(exc.value.detail)

    def test_verify_jwt_token_expired(self, monkeypatch):
        """Test verify_jwt_token raises 401 on ExpiredSignatureError."""
        monkeypatch.setattr(auth_module, "get_public_keys", lambda: "pubkey")

        def fake_decode(*a, **k):
            raise pyjwt.ExpiredSignatureError()

        monkeypatch.setattr(auth_module.jwt, "decode", fake_decode)
        with pytest.raises(HTTPException) as exc:
            auth_module.verify_jwt_token("token")
        assert exc.value.status_code == 401
        assert "Token expired" in str(exc.value.detail)

    def test_verify_jwt_token_invalid(self, monkeypatch):
        """Test verify_jwt_token raises 401 on InvalidTokenError."""
        monkeypatch.setattr(auth_module, "get_public_keys", lambda: "pubkey")

        def fake_decode(*a, **k):
            raise pyjwt.InvalidTokenError()

        monkeypatch.setattr(auth_module.jwt, "decode", fake_decode)
        with pytest.raises(HTTPException) as exc:
            auth_module.verify_jwt_token("token")
        assert exc.value.status_code == 401
        assert "Invalid token" in str(exc.value.detail)

    def test_verify_jwt_token_generic_exception(self, monkeypatch):
        """Test verify_jwt_token raises 503 on generic exception."""
        monkeypatch.setattr(auth_module, "get_public_keys", lambda: "pubkey")

        def fake_decode(*a, **k):
            raise Exception("fail")

        monkeypatch.setattr(auth_module.jwt, "decode", fake_decode)
        with pytest.raises(HTTPException) as exc:
            auth_module.verify_jwt_token("token")
        assert exc.value.status_code == 503
        assert "Authentication service unavailable" in str(exc.value.detail)

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
