from unittest.mock import Mock, patch
import requests
import app.auth as auth
import pytest
import app.services as services
import httpx


class TestAuth:
    """Test authentication-related functions."""
    def test_get_discord_jwt_success(self, monkeypatch):

        fake_token = "fake.jwt.token"

        class FakeResp:
            status_code = 200

            def json(self):
                return {"access_token": fake_token, "expires_in": 3600}

        monkeypatch.setenv("KEYCLOAK_URL", "https://kc.example.com")
        monkeypatch.setenv("KEYCLOAK_REALM", "realm")
        monkeypatch.setenv("DISCORD_CLIENT_ID", "cid")
        monkeypatch.setenv("DISCORD_CLIENT_SECRET", "secret")

        with patch("app.auth.requests.post", return_value=FakeResp()):
            # reset cache
            auth._discord_jwt = None
            auth._discord_jwt_expiry = 0

            token = auth.get_discord_jwt()
            assert token == fake_token
            # subsequent call should use cache
            token2 = auth.get_discord_jwt()
            assert token2 == fake_token


    def test_get_discord_jwt_failure(self, monkeypatch):

        monkeypatch.setenv("KEYCLOAK_URL", "https://kc.example.com")
        monkeypatch.setenv("KEYCLOAK_REALM", "realm")
        monkeypatch.setenv("DISCORD_CLIENT_ID", "cid")
        monkeypatch.setenv("DISCORD_CLIENT_SECRET", "secret")

        with patch("app.auth.requests.post", side_effect=requests.RequestException("netfail")):
            auth._discord_jwt = None
            auth._discord_jwt_expiry = 0
            token = auth.get_discord_jwt()
            assert token is None

class TestGetUserCardID:
    """Test get_user_card_id function."""
    def test_get_user_card_id_found(self, monkeypatch):
        import app.auth as auth

        class FakeResult:
            def __init__(self, data):
                self.data = data

        class FakeQuery:
            def select(self, *a, **k):
                return self

            def eq(self, *a, **k):
                return self

            def execute(self):
                return FakeResult([{"card_id": 12345}])

        class FakeClient:
            def table(self, name):
                return FakeQuery()

        monkeypatch.setattr(auth, "get_supabase", lambda: FakeClient())

        card = auth.get_user_card_id("discord-1")
        assert card == 12345


    def test_get_user_card_id_not_linked(self, monkeypatch):

        class FakeResult:
            def __init__(self, data):
                self.data = data

        class FakeQuery:
            def select(self, *a, **k):
                return self

            def eq(self, *a, **k):
                return self

            def execute(self):
                return FakeResult([])

        class FakeClient:
            def table(self, name):
                return FakeQuery()

        monkeypatch.setattr(auth, "get_supabase", lambda: FakeClient())

        with pytest.raises(auth.UserNotLinkedError):
            auth.get_user_card_id("discord-2")



class TestUserServiceClient:
    """Test UserServiceClient methods."""
    @pytest.mark.asyncio
    async def test_service_client_http_error(self, monkeypatch):

        # make AsyncClient.get raise HTTPError
        fake_exc = httpx.HTTPError("boom")

        async def fake_get(*a, **k):
            raise fake_exc

        mock_client = Mock()
        mock_client.get = fake_get

        # Patch AsyncClient context manager to return object with get that raises
        class FakeAsyncClientCtx:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return mock_client

            async def __aexit__(self, *a):
                return False

        monkeypatch.setattr(services.httpx, "AsyncClient", FakeAsyncClientCtx)

        client = services.ServiceClient("http://x")
        with pytest.raises(httpx.HTTPError):
            await client.get("/health")
