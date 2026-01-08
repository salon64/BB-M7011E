import logging
import sys
from app.config import settings


def setup_logging():
    """
    Configures the root logger for the application.
    """
    log_level = getattr(settings, "log_level", "INFO").upper()
    valid_levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
    if log_level not in valid_levels:
        log_level = "INFO"
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
