from app import database


def test_get_supabase_client(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://fake-url.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "fake-key")

    class DummyClient:
        pass

    monkeypatch.setattr(database, "create_client", lambda url, key: DummyClient())

    client = database.get_supabase_client()
    assert isinstance(client, DummyClient)
