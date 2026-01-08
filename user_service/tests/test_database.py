import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Add repo root for common

from common import database


def test_get_supabase_client(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://fake-url.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "fake-key")

    class DummyClient:
        pass

    monkeypatch.setattr(database, "create_client", lambda url, key: DummyClient())
    monkeypatch.setattr(database, "_supabase_client", None)

    client = database.get_supabase_client()
    assert isinstance(client, DummyClient)


def test_get_supabase(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://fake-url.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "fake-key")

    class DummyClient:
        pass

    monkeypatch.setattr(database, "create_client", lambda url, key: DummyClient())
    monkeypatch.setattr(database, "_supabase_client", None)

    client = database.get_supabase()
    assert isinstance(client, DummyClient)

    monkeypatch.setattr(database, "create_client", lambda url, key: DummyClient())
    monkeypatch.setattr(database, "_supabase_client", None)

    client = database.get_supabase()
    assert isinstance(client, DummyClient)
