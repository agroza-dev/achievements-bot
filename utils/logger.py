import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

from core.config import settings
from utils.log_filters import ProjectOnlyFilter


def setup_logging() -> None:
    log_dir = settings.logs.path
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # важно: корень всегда DEBUG

    # защита от повторной инициализации
    if root_logger.handlers:
        return

    # ---------- FILE ----------
    file_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, "bot.log"),
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG if settings.app.debug else logging.INFO)
    file_handler.setFormatter(formatter)

    # ---------- CONSOLE ----------
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.app.debug else logging.WARNING)
    console_handler.setFormatter(formatter)

    console_handler.addFilter(ProjectOnlyFilter(("bot", "core", "utils")))


    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

setup_logging()

logger = logging.getLogger(__name__)
