import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Add repo root for common

import os
from unittest.mock import patch


class TestBotCommands:
    """Test Discord bot commands."""

    def test_env_defaults(self):
        """Test that environment variables have sensible defaults."""
        # COMMAND_PREFIX defaults to "!" if not set
        prefix = os.getenv("COMMAND_PREFIX", "!")
        assert prefix == "!"


class TestMainFunction:
    """Test main entry point."""

    def test_main_no_token(self, monkeypatch, caplog):
        """Test main() exits early when DISCORD_TOKEN is not set."""
        import importlib

        monkeypatch.delenv("DISCORD_TOKEN", raising=False)

        # Need to reload to pick up env change
        import app.main as main_module
        importlib.reload(main_module)

        # main() should return early without running bot
        result = main_module.main()
        assert result is None

    def test_main_with_token(self, monkeypatch):
        """Test main() runs bot when token is set."""
        import importlib

        monkeypatch.setenv("DISCORD_TOKEN", "test-token")
        monkeypatch.setenv("COMMAND_PREFIX", "!")

        import app.main as main_module
        importlib.reload(main_module)

        # Mock the bot.run to avoid actually starting
        with patch.object(main_module.bot, "run") as mock_run:
            main_module.main()
            mock_run.assert_called_once_with("test-token")

    def test_main_keyboard_interrupt(self, monkeypatch):
        """Test main() handles KeyboardInterrupt gracefully."""
        import importlib

        monkeypatch.setenv("DISCORD_TOKEN", "test-token")
        monkeypatch.setenv("COMMAND_PREFIX", "!")

        import app.main as main_module
        importlib.reload(main_module)

        with patch.object(main_module.bot, "run", side_effect=KeyboardInterrupt):
            # Should not raise, just log and exit
            main_module.main()


class TestSignalHandler:
    """Test signal handler functionality."""

    def test_signal_handler_setup(self, monkeypatch):
        """Test that signal handlers are registered."""
        import importlib
        import signal

        monkeypatch.setenv("DISCORD_TOKEN", "test-token")
        monkeypatch.setenv("COMMAND_PREFIX", "!")

        import app.main as main_module
        importlib.reload(main_module)

        with patch.object(main_module.bot, "run"):
            with patch("signal.signal") as mock_signal:
                main_module.main()
                # Check both SIGTERM and SIGINT are registered
                calls = [call[0][0] for call in mock_signal.call_args_list]
                assert signal.SIGTERM in calls
                assert signal.SIGINT in calls
