import logging
import sys
from app.config import settings


def setup_logging():
    """
    Configures the root logger for the application.
    """
    log_level = settings.log_level.upper()

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
