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
    # monkeypatch the global bot and get_supabase_client
    monkeypatch.setattr(bot_main, "bot", fake_bot)
    monkeypatch.setattr(bot_main, "get_supabase_client", lambda: object())

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
            self.sent = AsyncMock()

        async def send(self, *a, **k):
            return await self.sent(*a, **k)

    ctx = Ctx()
    err = commands.CommandNotFound()

    await bot_main.on_command_error(ctx, err)
    assert ctx.sent.await_count == 1
    # collect all positional and keyword args into a single string for robust checking
    call = ctx.sent.await_args
    args = call[0][0] if call and call[0] else ()
    kwargs = call[0][1] if call and call[0] else {}
    sent_text = " ".join(map(str, args)) + " " + " ".join(f"{k}={v}" for k, v in kwargs.items())
    assert "Command not found" in sent_text


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
            self.sent = AsyncMock()

        async def send(self, *a, **k):
            return await self.sent(*a, **k)

    ctx = Ctx()
    # MissingRequiredArgument expects a 'param' - provide a simple namespace with name
    # construct an instance without calling the constructor (which may access param attrs)
    err = object.__new__(commands.MissingRequiredArgument)
    err.param = SimpleNamespace(name="item_id")

    await bot_main.on_command_error(ctx, err)
    assert ctx.sent.await_count == 1
    call = ctx.sent.await_args
    args = call[0][0] if call and call[0] else ()
    kwargs = call[0][1] if call and call[0] else {}
    sent_text = " ".join(map(str, args)) + " " + " ".join(f"{k}={v}" for k, v in kwargs.items())
    assert "Missing required argument" in sent_text


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
            self.sent = AsyncMock()

        async def send(self, *a, **k):
            return await self.sent(*a, **k)

    ctx = Ctx()
    # CommandInvokeError wraps original exception
    err = commands.CommandInvokeError(UserNotLinkedError("12"))

    # set ACCOUNT_LINK_URL to known value to assert in message
    monkeypatch.setenv("ACCOUNT_LINK_URL", "https://link.example.com")
    bot_main.ACCOUNT_LINK_URL = "https://link.example.com"

    await bot_main.on_command_error(ctx, err)
    assert ctx.sent.await_count == 1
    call = ctx.sent.await_args
    args = call[0][0] if call and call[0] else ()
    kwargs = call[0][1] if call and call[0] else {}
    sent_text = " ".join(map(str, args)) + " " + " ".join(f"{k}={v}" for k, v in kwargs.items())
    assert ("link your account" in sent_text.lower()) or ("link" in sent_text.lower() and "account" in sent_text.lower())
