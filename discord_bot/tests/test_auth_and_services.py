from unittest.mock import Mock, patch
import requests
import app.auth as auth
import pytest
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

        class FakeJwtResp:
            status_code = 200
            
            def json(self):
                return {"access_token": "fake_token", "expires_in": 3600}
        
        class FakeCardResp:
            status_code = 200
            
            def json(self):
                return {"card_id": 12345}
        
        monkeypatch.setenv("KEYCLOAK_URL", "https://kc.example.com")
        monkeypatch.setenv("KEYCLOAK_REALM", "realm")
        monkeypatch.setenv("DISCORD_CLIENT_ID", "cid")
        monkeypatch.setenv("DISCORD_CLIENT_SECRET", "secret")
        monkeypatch.setenv("USER_SERVICE_URL", "http://user-service:8000")
        
        # Mock both requests.post calls: one for JWT, one for discord lookup
        with patch("app.auth.requests.post") as mock_post:
            # First call returns JWT, second call returns card_id
            mock_post.side_effect = [
                FakeJwtResp(),  # JWT token response
                FakeCardResp(),  # Discord lookup response
            ]
            
            # Reset cache
            auth._discord_jwt = None
            auth._discord_jwt_expiry = 0
            
            card = auth.get_user_card_id("discord-1")
            assert card == "12345"


    def test_get_user_card_id_not_linked(self, monkeypatch):
        import app.auth as auth

        class FakeJwtResp:
            status_code = 200
            
            def json(self):
                return {"access_token": "token", "expires_in": 3600}
        
        class FakeNotFoundResp:
            status_code = 404
            
            def json(self):
                return {}
        
        monkeypatch.setenv("KEYCLOAK_URL", "https://kc.example.com")
        monkeypatch.setenv("KEYCLOAK_REALM", "realm")
        monkeypatch.setenv("DISCORD_CLIENT_ID", "cid")
        monkeypatch.setenv("DISCORD_CLIENT_SECRET", "secret")
        monkeypatch.setenv("USER_SERVICE_URL", "http://user-service:8000")
        
        with patch("app.auth.requests.post") as mock_post:
            # First call returns JWT, second returns 404
            mock_post.side_effect = [
                FakeJwtResp(),  # JWT token response
                FakeNotFoundResp(),  # Discord lookup not found
            ]
            
            # Reset cache
            auth._discord_jwt = None
            auth._discord_jwt_expiry = 0
            
            with pytest.raises(auth.UserNotLinkedError):
                auth.get_user_card_id("discord-2")
