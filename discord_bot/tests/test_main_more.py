import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_buy_success(monkeypatch):
    import main as bot_main

    ctx = type("C", (), {})()
    # prepare message/author
    class Author:
        id = 123

    class Message:
        author = Author()

    ctx.message = Message()
    ctx.last_sent = None
    ctx.sent_count = 0

    async def send(*a, **k):
        ctx.last_sent = " ".join(map(str, a))
        ctx.sent_count += 1

    ctx.send = send

    monkeypatch.setattr("app.auth.get_user_card_id", lambda discord_id: 123)
    monkeypatch.setattr("app.auth.get_discord_jwt", lambda: "tok")

    class ItemResp:
        status_code = 200

        def json(self):
            return {"name": "TestItem", "price": 250}

    class PaymentResp:
        status_code = 200

        def json(self):
            return {"new_balance": 750}

    class FakeAsyncClientCtx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, *a, **k):
            if "/items/fetch_info" in url:
                return ItemResp()
            return PaymentResp()

    monkeypatch.setattr(bot_main.httpx, "AsyncClient", FakeAsyncClientCtx)

    await bot_main.buy(ctx, item_id="item-1")
    assert ctx.sent_count == 1
    assert "Purchase Successful" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_buy_insufficient_funds(monkeypatch):
    import main as bot_main

    ctx = type("C", (), {})()
    class Author:
        id = 124

    class Message:
        author = Author()

    ctx.message = Message()
    ctx.last_sent = None
    ctx.sent_count = 0

    async def send(*a, **k):
        ctx.last_sent = " ".join(map(str, a))
        ctx.sent_count += 1

    ctx.send = send

    monkeypatch.setattr("app.auth.get_user_card_id", lambda discord_id: 124)
    monkeypatch.setattr("app.auth.get_discord_jwt", lambda: "tok")

    class ItemResp:
        status_code = 200

        def json(self):
            return {"name": "Expensive", "price": 10000}

    class PaymentResp:
        status_code = 402

        def json(self):
            return {"detail": "Insufficient funds"}

    class FakeAsyncClientCtx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, *a, **k):
            if "/items/fetch_info" in url:
                return ItemResp()
            return PaymentResp()

    monkeypatch.setattr(bot_main.httpx, "AsyncClient", FakeAsyncClientCtx)

    await bot_main.buy(ctx, item_id="exp")
    assert ctx.sent_count == 1
    assert "Insufficient funds" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_transactions_success(monkeypatch):
    import main as bot_main

    ctx = type("C", (), {})()
    class Author:
        id = 200

    class Message:
        author = Author()

    ctx.message = Message()
    ctx.last_sent = None
    ctx.sent_count = 0

    async def send(*a, **k):
        ctx.last_sent = " ".join(map(str, a))
        ctx.sent_count += 1

    ctx.send = send

    monkeypatch.setattr("app.auth.get_user_card_id", lambda discord_id: 200)
    monkeypatch.setattr("app.auth.get_discord_jwt", lambda: "tok")

    class Resp:
        status_code = 200

        def json(self):
            return {"transactions": [{"id": "t1", "user": 200, "amount": 150, "created_at": "now"}]}

    class FakeAsyncClientCtx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, *a, **k):
            return Resp()

    monkeypatch.setattr(bot_main.httpx, "AsyncClient", FakeAsyncClientCtx)

    await bot_main.transactions(ctx)
    assert ctx.sent_count == 1
    assert "Transaction History" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_add_funds_success(monkeypatch):
    import main as bot_main

    ctx = type("C", (), {})()
    class Author:
        id = 400

    class Attachment:
        content_type = "image/png"
        url = "http://example.com/img.png"

    class Message:
        author = Author()
        attachments = [Attachment()]

    ctx.message = Message()
    ctx.last_sent = None
    ctx.sent_count = 0

    async def send(*a, **k):
        ctx.last_sent = " ".join(map(str, a))
        ctx.sent_count += 1

    ctx.send = send

    monkeypatch.setattr("app.auth.get_user_card_id", lambda discord_id: 400)
    monkeypatch.setattr("app.auth.get_discord_jwt", lambda: "tok")

    class Resp:
        status_code = 200

        def json(self):
            return {"new_balance": 2000}

    class FakeAsyncClientCtx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, *a, **k):
            return Resp()

    monkeypatch.setattr(bot_main.httpx, "AsyncClient", FakeAsyncClientCtx)

    await bot_main.add_funds(ctx, amount="20")
    assert ctx.sent_count == 1
    assert "Funds Added Successfully" in (ctx.last_sent or "")


def test_auth_test_success(monkeypatch):
    import main as bot_main
    import jwt

    ctx = type("C", (), {})()
    class Author:
        id = 500

    class Message:
        author = Author()

    ctx.message = Message()
    ctx.last_sent = None
    ctx.sent_count = 0

    async def send(*a, **k):
        ctx.last_sent = " ".join(map(str, a))
        ctx.sent_count += 1

    ctx.send = send

    monkeypatch.setattr("app.auth.get_user_card_id", lambda discord_id: 500)
    monkeypatch.setattr("app.auth.get_discord_jwt", lambda: "header.payload.signature")
    monkeypatch.setattr(jwt, "decode", lambda token, **k: {"exp": 9999999999})

    import asyncio
    coro = bot_main.auth_test(ctx)
    asyncio.get_event_loop().run_until_complete(coro)
    assert ctx.sent_count == 1
    assert "Authentication test" in (ctx.last_sent or "")
