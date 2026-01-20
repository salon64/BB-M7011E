from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_on_ready_sets_presence_and_supabase(monkeypatch):
    import main as bot_main

    # Fake bot with required attributes
    class FakeUser:
        name = "TestBot"
        id = 123

    class FakeBot:
        def __init__(self):
            self.user = FakeUser()
            self.guilds = [1, 2]
            self.change_presence = AsyncMock()

    fake_bot = FakeBot()
    # monkeypatch the global bot
    monkeypatch.setattr(bot_main, "bot", fake_bot)

    await bot_main.on_ready()

    # change_presence should have been awaited once
    assert fake_bot.change_presence.await_count == 1


@pytest.mark.asyncio
async def test_on_command_error_command_not_found(monkeypatch):
    import main as bot_main
    from discord.ext import commands

    # ensure a known prefix
    monkeypatch.setenv("COMMAND_PREFIX", "!")
    bot_main.COMMAND_PREFIX = "!"

    class FakeAuthor:
        id = 10

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None
            self.sent_count = 0

        async def send(self, *a, **k):
            # store a simple string representation of the sent message
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            self.sent_count += 1
            return None

    ctx = Ctx()
    err = commands.CommandNotFound()

    await bot_main.on_command_error(ctx, err)
    assert ctx.sent_count == 1
    assert "Command not found" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_on_command_error_missing_required_argument(monkeypatch):
    import main as bot_main
    from discord.ext import commands

    class FakeAuthor:
        id = 11

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None
            self.sent_count = 0

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            self.sent_count += 1
            return None

    ctx = Ctx()
    # MissingRequiredArgument expects a 'param' - provide a simple namespace with name
    # create a safe subclass to avoid base class constructor side-effects

    class DummyMissing(commands.MissingRequiredArgument):
        def __init__(self):
            self.param = SimpleNamespace(name="item_id")

    err = DummyMissing()

    await bot_main.on_command_error(ctx, err)
    assert ctx.sent_count == 1
    assert "Missing required argument" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_on_command_error_user_not_linked(monkeypatch):
    import main as bot_main
    from discord.ext import commands
    from app.auth import UserNotLinkedError

    class FakeAuthor:
        id = 12

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None
            self.sent_count = 0

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            self.sent_count += 1
            return None

    ctx = Ctx()
    # CommandInvokeError wraps original exception
    err = commands.CommandInvokeError(UserNotLinkedError("12"))

    # set ACCOUNT_LINK_URL to known value to assert in message
    monkeypatch.setenv("ACCOUNT_LINK_URL", "https://link.example.com")
    bot_main.ACCOUNT_LINK_URL = "https://link.example.com"

    await bot_main.on_command_error(ctx, err)
    assert ctx.sent_count == 1
    sent_text = (ctx.last_sent or "").lower()
    assert ("link your account" in sent_text) or ("link" in sent_text and "account" in sent_text)


@pytest.mark.asyncio
async def test_on_command_error_missing_permissions(monkeypatch):
    """Test error handler for missing permissions."""
    import main as bot_main
    from discord.ext import commands

    class FakeAuthor:
        id = 13

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None
            self.sent_count = 0

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            self.sent_count += 1
            return None

    ctx = Ctx()
    err = commands.MissingPermissions(["administrator"])

    await bot_main.on_command_error(ctx, err)
    assert ctx.sent_count == 1
    assert "permission" in (ctx.last_sent or "").lower()


@pytest.mark.asyncio
async def test_on_command_error_generic(monkeypatch):
    """Test error handler for generic errors."""
    import main as bot_main

    class FakeAuthor:
        id = 14

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None
            self.sent_count = 0

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            self.sent_count += 1
            return None

    ctx = Ctx()
    err = RuntimeError("Some unexpected error")

    await bot_main.on_command_error(ctx, err)
    assert ctx.sent_count == 1
    assert "error occurred" in (ctx.last_sent or "").lower()


@pytest.mark.asyncio
async def test_ping_command(monkeypatch):
    """Test ping command."""
    import main as bot_main

    class FakeAuthor:
        id = 100
        name = "TestUser"

        def __str__(self):
            return self.name

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    # Mock bot.latency
    class FakeBot:
        latency = 0.05  # 50ms

    monkeypatch.setattr(bot_main, "bot", FakeBot())

    ctx = Ctx()
    await bot_main.ping(ctx)
    assert "Pong" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_balance_command_success(monkeypatch):
    """Test balance command with successful response."""
    import main as bot_main
    from unittest.mock import patch, AsyncMock

    class FakeAuthor:
        id = 200

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    # Mock get_user_card_id and get_discord_jwt
    with patch.object(bot_main, "get_user_card_id", return_value="12345"):
        with patch.object(bot_main, "get_discord_jwt", return_value="fake-jwt"):
            # Mock the httpx AsyncClient
            mock_response = AsyncMock()
            mock_response.status_code = 200
            # json() is a regular method, not async
            mock_response.json = lambda: {
                "first_name": "Test",
                "last_name": "User",
                "balance": 10050,  # 100.50 SEK
                "active": True
            }

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("main.httpx.AsyncClient", return_value=mock_client):
                ctx = Ctx()
                await bot_main.balance(ctx)
                assert "Balance" in (ctx.last_sent or "") or "balance" in (ctx.last_sent or "").lower()


@pytest.mark.asyncio
async def test_balance_command_no_jwt(monkeypatch):
    """Test balance command when JWT fetch fails."""
    import main as bot_main
    from unittest.mock import patch

    class FakeAuthor:
        id = 201

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    with patch.object(bot_main, "get_user_card_id", return_value="12345"):
        with patch.object(bot_main, "get_discord_jwt", return_value=None):
            ctx = Ctx()
            await bot_main.balance(ctx)
            assert "Failed to authenticate" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_balance_command_user_not_found(monkeypatch):
    """Test balance command when user not found (404)."""
    import main as bot_main
    from unittest.mock import patch, AsyncMock

    class FakeAuthor:
        id = 202

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    with patch.object(bot_main, "get_user_card_id", return_value="12345"):
        with patch.object(bot_main, "get_discord_jwt", return_value="fake-jwt"):
            mock_response = AsyncMock()
            mock_response.status_code = 404

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("main.httpx.AsyncClient", return_value=mock_client):
                ctx = Ctx()
                await bot_main.balance(ctx)
                assert "not found" in (ctx.last_sent or "").lower()


@pytest.mark.asyncio
async def test_balance_command_server_error(monkeypatch):
    """Test balance command when server returns error."""
    import main as bot_main
    from unittest.mock import patch, AsyncMock

    class FakeAuthor:
        id = 203

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    with patch.object(bot_main, "get_user_card_id", return_value="12345"):
        with patch.object(bot_main, "get_discord_jwt", return_value="fake-jwt"):
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("main.httpx.AsyncClient", return_value=mock_client):
                ctx = Ctx()
                await bot_main.balance(ctx)
                assert "Failed to fetch" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_balance_command_request_error(monkeypatch):
    """Test balance command when request fails."""
    import main as bot_main
    import httpx
    from unittest.mock import patch, AsyncMock

    class FakeAuthor:
        id = 204

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    with patch.object(bot_main, "get_user_card_id", return_value="12345"):
        with patch.object(bot_main, "get_discord_jwt", return_value="fake-jwt"):
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("main.httpx.AsyncClient", return_value=mock_client):
                ctx = Ctx()
                await bot_main.balance(ctx)
                assert "Could not connect" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_items_command_success(monkeypatch):
    """Test items command with successful response."""
    import main as bot_main
    from unittest.mock import patch, AsyncMock

    class FakeAuthor:
        id = 300

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    with patch.object(bot_main, "get_user_card_id", return_value="12345"):
        with patch.object(bot_main, "get_discord_jwt", return_value="fake-jwt"):
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = lambda: {
                "items": [
                    {"id": "item1", "name": "Coffee", "price": 2500},
                    {"id": "item2", "name": "Sandwich", "price": 5000},
                ]
            }

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("main.httpx.AsyncClient", return_value=mock_client):
                ctx = Ctx()
                await bot_main.items(ctx)
                assert "Available Items" in (ctx.last_sent or "")
                assert "Coffee" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_items_command_empty(monkeypatch):
    """Test items command with no items."""
    import main as bot_main
    from unittest.mock import patch, AsyncMock

    class FakeAuthor:
        id = 301

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    with patch.object(bot_main, "get_user_card_id", return_value="12345"):
        with patch.object(bot_main, "get_discord_jwt", return_value="fake-jwt"):
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = lambda: {"items": []}

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("main.httpx.AsyncClient", return_value=mock_client):
                ctx = Ctx()
                await bot_main.items(ctx)
                assert "No items available" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_items_command_no_jwt(monkeypatch):
    """Test items command when JWT fetch fails."""
    import main as bot_main
    from unittest.mock import patch

    class FakeAuthor:
        id = 302

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    with patch.object(bot_main, "get_user_card_id", return_value="12345"):
        with patch.object(bot_main, "get_discord_jwt", return_value=None):
            ctx = Ctx()
            await bot_main.items(ctx)
            assert "Failed to authenticate" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_items_command_error_response(monkeypatch):
    """Test items command with error response."""
    import main as bot_main
    from unittest.mock import patch, AsyncMock

    class FakeAuthor:
        id = 303

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    with patch.object(bot_main, "get_user_card_id", return_value="12345"):
        with patch.object(bot_main, "get_discord_jwt", return_value="fake-jwt"):
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("main.httpx.AsyncClient", return_value=mock_client):
                ctx = Ctx()
                await bot_main.items(ctx)
                assert "Failed to fetch items" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_items_command_request_error(monkeypatch):
    """Test items command when request fails."""
    import main as bot_main
    import httpx
    from unittest.mock import patch, AsyncMock

    class FakeAuthor:
        id = 304

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    with patch.object(bot_main, "get_user_card_id", return_value="12345"):
        with patch.object(bot_main, "get_discord_jwt", return_value="fake-jwt"):
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("main.httpx.AsyncClient", return_value=mock_client):
                ctx = Ctx()
                await bot_main.items(ctx)
                assert "Could not connect" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_items_command_many_items(monkeypatch):
    """Test items command with more than 20 items (truncation)."""
    import main as bot_main
    from unittest.mock import patch, AsyncMock

    class FakeAuthor:
        id = 305

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    with patch.object(bot_main, "get_user_card_id", return_value="12345"):
        with patch.object(bot_main, "get_discord_jwt", return_value="fake-jwt"):
            # Create more than 20 items
            items_list = [{"id": f"item{i}", "name": f"Item {i}", "price": 1000 + i * 100}
                          for i in range(25)]
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = lambda: {"items": items_list}

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("main.httpx.AsyncClient", return_value=mock_client):
                ctx = Ctx()
                await bot_main.items(ctx)
                assert "more items" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_buy_command_no_item_id(monkeypatch):
    """Test buy command without item_id."""
    import main as bot_main

    class FakeAuthor:
        id = 400

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    # Set the command prefix
    monkeypatch.setattr(bot_main, "COMMAND_PREFIX", "!")

    ctx = Ctx()
    await bot_main.buy(ctx, item_id=None)
    assert "specify an item ID" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_buy_command_no_jwt(monkeypatch):
    """Test buy command when JWT fetch fails."""
    import main as bot_main
    from unittest.mock import patch

    class FakeAuthor:
        id = 401

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    with patch.object(bot_main, "get_user_card_id", return_value="12345"):
        with patch.object(bot_main, "get_discord_jwt", return_value=None):
            ctx = Ctx()
            await bot_main.buy(ctx, item_id="item1")
            assert "Failed to authenticate" in (ctx.last_sent or "")


@pytest.mark.asyncio
async def test_buy_command_item_not_found(monkeypatch):
    """Test buy command when item is not found."""
    import main as bot_main
    from unittest.mock import patch, AsyncMock

    class FakeAuthor:
        id = 402

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    with patch.object(bot_main, "get_user_card_id", return_value="12345"):
        with patch.object(bot_main, "get_discord_jwt", return_value="fake-jwt"):
            mock_response = AsyncMock()
            mock_response.status_code = 404

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("main.httpx.AsyncClient", return_value=mock_client):
                ctx = Ctx()
                await bot_main.buy(ctx, item_id="nonexistent")
                assert "not found" in (ctx.last_sent or "").lower()


@pytest.mark.asyncio
async def test_buy_command_success(monkeypatch):
    """Test buy command with successful purchase."""
    import main as bot_main
    from unittest.mock import patch, AsyncMock

    class FakeAuthor:
        id = 403

    class FakeMessage:
        author = FakeAuthor()

    class Ctx:
        def __init__(self):
            self.message = FakeMessage()
            self.last_sent = None

        async def send(self, *a, **k):
            try:
                self.last_sent = " ".join(map(str, a))
            except Exception:
                self.last_sent = str(a)
            return None

    with patch.object(bot_main, "get_user_card_id", return_value="12345"):
        with patch.object(bot_main, "get_discord_jwt", return_value="fake-jwt"):
            # First call for item info, second for payment
            item_response = AsyncMock()
            item_response.status_code = 200
            item_response.json = lambda: {"name": "Coffee", "price": 2500}

            payment_response = AsyncMock()
            payment_response.status_code = 200
            payment_response.json = lambda: {"new_balance": 7500}

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=[item_response, payment_response])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("main.httpx.AsyncClient", return_value=mock_client):
                ctx = Ctx()
                await bot_main.buy(ctx, item_id="coffee")
                assert "Purchase Successful" in (ctx.last_sent or "")
