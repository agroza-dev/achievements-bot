"""Утилиты для работы с часовыми поясами."""

# Маппинг языковых кодов Telegram на часовые пояса
# https://core.telegram.org/bots/api#user
LANGUAGE_TO_TIMEZONE = {
    # Русский - Москва (UTC+3)
    "ru": "Europe/Moscow",

    # Украинский - Киев (UTC+2/UTC+3)
    "uk": "Europe/Kiev",

    # Белорусский - Минск (UTC+3)
    "be": "Europe/Minsk",

    # Английский - UTC
    "en": "UTC",

    # Испанский - Мадрид (UTC+1/UTC+2)
    "es": "Europe/Madrid",

    # Португальский - Лиссабон (UTC+0/UTC+1)
    "pt": "Europe/Lisbon",

    # Немецкий - Берлин (UTC+1/UTC+2)
    "de": "Europe/Berlin",

    # Французский - Париж (UTC+1/UTC+2)
    "fr": "Europe/Paris",

    # Итальянский - Рим (UTC+1/UTC+2)
    "it": "Europe/Rome",

    # Польский - Варшава (UTC+1/UTC+2)
    "pl": "Europe/Warsaw",

    # Турецкий - Стамбул (UTC+3)
    "tr": "Europe/Istanbul",

    # Казахский - Алматы (UTC+6)
    "kk": "Asia/Almaty",

    # Китайский - Шанхай (UTC+8)
    "zh": "Asia/Shanghai",

    # Японский - Токио (UTC+9)
    "ja": "Asia/Tokyo",

    # Корейский - Сеул (UTC+9)
    "ko": "Asia/Seoul",
}


def get_timezone_by_language(language_code: str | None) -> str:
    """
    Получить часовой пояс по языковому коду Telegram.

    Args:
        language_code: Языковой код пользователя из Telegram

    Returns:
        Название часового пояса в формате IANA (например, "Europe/Moscow")
    """
    if not language_code:
        return "UTC"

    # Извлекаем базовый язык (без региона)
    # Например: "ru" из "ru-RU", "pt" из "pt-BR"
    base_lang = language_code.split("-")[0].lower()

    return LANGUAGE_TO_TIMEZONE.get(base_lang, "UTC")
