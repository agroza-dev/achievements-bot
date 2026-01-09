import logging
import os
from logging.handlers import TimedRotatingFileHandler

from core.config import settings


def setup_logging() -> None:
    log_dir = settings.logs.path
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "bot.log")

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if any(isinstance(h, TimedRotatingFileHandler) for h in root_logger.handlers):
        return

    handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG if settings.app.debug else logging.INFO)
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)


setup_logging()

logger = logging.getLogger(__name__)
