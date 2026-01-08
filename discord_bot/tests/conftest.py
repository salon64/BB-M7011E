import pytest


@pytest.fixture(autouse=True)
def supabase_env(monkeypatch):
    """Ensure SUPABASE env vars are set for tests to avoid client initialization errors."""
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:8000")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    yield
