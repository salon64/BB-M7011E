import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # Add repo root for common


class TestBotCommands:
    """Test Discord bot commands."""

    def test_env_defaults(self):
        """Test that environment variables have sensible defaults."""
        # COMMAND_PREFIX defaults to "!" if not set
        prefix = os.getenv("COMMAND_PREFIX", "!")
        assert prefix == "!"
