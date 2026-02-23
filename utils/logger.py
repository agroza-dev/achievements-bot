import json
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

from core.config import settings
from utils.log_filters import ProjectOnlyFilter

# Цвета для разных уровней логирования
COLORS = {
    logging.DEBUG: "\033[36m",      # Cyan
    logging.INFO: "\033[32m",       # Green
    logging.WARNING: "\033[33m",    # Yellow
    logging.ERROR: "\033[31m",      # Red
    logging.CRITICAL: "\033[35m",   # Magenta
}
RESET = "\033[0m"


def prettify(obj, indent: int = 0) -> str:
    """
    Helper для красивого форматирования объектов в логах.
    Используйте в logger.info(f"Message: {prettify(obj)}")
    """
    prefix = "  " * indent

    if obj is None:
        return "None"

    if isinstance(obj, bool):
        return str(obj).lower()

    if isinstance(obj, (int, float)):
        return str(obj)

    if isinstance(obj, str):
        if len(obj) > 60:
            return f'"{obj[:60]}..."'
        return f'"{obj}"'

    if isinstance(obj, (list, tuple, set)):
        if not obj:
            return "[]"
        if len(obj) <= 3 and all(isinstance(x, (int, float, str)) for x in obj):
            items = ", ".join(prettify(x, 0) for x in obj)
            return f"[{items}]"
        items = [prettify(x, indent + 1) for x in obj]
        return "[\n" + prefix + "  " + (",\n" + prefix + "  ").join(items) + "\n" + prefix + "]"

    if isinstance(obj, dict):
        if not obj:
            return "{}"
        try:
            return json.dumps(obj, indent=2, ensure_ascii=False, default=lambda x: str(x))
        except (TypeError, ValueError):
            items = []
            for key, value in obj.items():
                items.append(f'{prettify(key, 0)}: {prettify(value, indent + 1)}')
            return "{\n" + prefix + "  " + (",\n" + prefix + "  ").join(items) + "\n" + prefix + "}"

    # Enum
    if hasattr(obj, 'name') and hasattr(obj, 'value'):
        return f"<{obj.__class__.__name__}.{obj.name}>"

    # Dataclass
    if hasattr(obj, '__dataclass_fields__'):
        lines = [f"{obj.__class__.__name__}:"]
        for field_name in obj.__dataclass_fields__:
            value = getattr(obj, field_name, None)
            formatted_value = prettify(value, indent + 1)
            # Если значение простое - в одну строку
            if isinstance(value, (int, float, str, bool, type(None))):
                lines.append(f"  {field_name}: {formatted_value}")
            else:
                lines.append(f"  {field_name}:\n{prefix}  {formatted_value}")
        return "\n".join(lines)

    # Telegram объекты и другие с __slots__ или __dict__
    if hasattr(obj, '__slots__') or hasattr(obj, '__dict__'):
        class_name = obj.__class__.__name__
        attrs = {}

        if hasattr(obj, '__slots__'):
            for slot in obj.__slots__:
                if not slot.startswith('_') and hasattr(obj, slot):
                    attrs[slot] = getattr(obj, slot)
        elif hasattr(obj, '__dict__'):
            attrs = {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}

        if not attrs:
            return f"<{class_name}>"

        lines = [f"{class_name}:"]
        for key, value in attrs.items():
            formatted_value = prettify(value, indent + 1)
            # Простые значения в одну строку
            if isinstance(value, (int, float, str, bool, type(None))):
                lines.append(f"  {key}: {formatted_value}")
            else:
                lines.append(f"  {key}:\n{prefix}  {formatted_value}")
        return "\n".join(lines)

    # По умолчанию
    return str(obj)


class ColoredFormatter(logging.Formatter):
    """Цветной formatter для консоли."""

    def format(self, record: logging.LogRecord) -> str:
        # Добавляем цвет в зависимости от уровня
        color = COLORS.get(record.levelno, "")
        record.levelname = f"{color}{record.levelname}{RESET}"
        return super().format(record)


def setup_logging() -> None:
    log_dir = settings.logs.path
    os.makedirs(log_dir, exist_ok=True)

    # ---------- ФОРМАТЫ ----------
    # Консоль: краткий формат с цветами
    console_format = ColoredFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Файл: полный формат с деталями
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

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
    file_handler.setFormatter(file_format)

    # ---------- CONSOLE ----------
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.app.debug else logging.WARNING)
    console_handler.setFormatter(console_format)
    console_handler.addFilter(ProjectOnlyFilter(("bot", "core", "utils")))


    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

setup_logging()

logger = logging.getLogger(__name__)
