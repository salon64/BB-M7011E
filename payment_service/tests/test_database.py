import pytest
from app import database

def test_get_supabase_client(monkeypatch):
    monkeypatch.setattr(database.settings, "supabase_url", "https://fake-url.supabase.co")
    monkeypatch.setattr(database.settings, "supabase_key", "fake-key")

    class DummyClient:
        pass
    monkeypatch.setattr(database, "create_client", lambda url, key: DummyClient())

    monkeypatch.setattr(database, "_supabase_client", None)

    client = database.get_supabase_client()
    assert isinstance(client, DummyClient)

def test_get_supabase(monkeypatch):

    monkeypatch.setattr(database.settings, "supabase_url", "https://fake-url.supabase.co")
    monkeypatch.setattr(database.settings, "supabase_key", "fake-key")
    class DummyClient:
        pass
    monkeypatch.setattr(database, "create_client", lambda url, key: DummyClient())
    monkeypatch.setattr(database, "_supabase_client", None)

    client = database.get_supabase()
    assert isinstance(client, DummyClient)