"""
Central logging setup.

Privacy rule for this project: health messages are sensitive personal data.
Log LENGTHS, IDs, categories and timings -- never the message text itself.
"""

import logging
import os
import sys

from app.core.request_context import get_request_id, get_user_id


class RequestContextFilter(logging.Filter):
    """Adds request_id and user_id to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.user_id = get_user_id()
        return True


_CONFIGURED = False


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-7s [req=%(request_id)s user=%(user_id)s] "
            "%(name)s: %(message)s"
        )
    )

    root = logging.getLogger("healthcare")
    root.setLevel(level)
    root.handlers = [handler]
    root.propagate = False

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the 'healthcare' namespace."""
    return logging.getLogger(f"healthcare.{name}")
