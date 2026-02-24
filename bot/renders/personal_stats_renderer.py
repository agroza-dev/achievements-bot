from datetime import UTC, datetime

from core.dto.personal_stats_dto import PersonalStatsDTO

# Иконки для типов операций
OPERATION_ICONS = {
    "reaction": "💎",      # реакция на сообщение
    "reaction_revert": "↩️",  # отмена реакции
    "tax": "🧾",          # налог
    "transfer": "💸",     # перевод между пользователями
}

# Иконки для подтипов операций (action)
ACTION_ICONS = {
    "added": "✨",        # добавление
    "removed": "🗑️",     # удаление
    "changed": "🔄",      # изменение
}


def _get_operation_icon(entry) -> str:
    """Получить иконку для типа операции"""
    # Для реакций показываем эмодзи из meta
    if entry.operation_type == "reaction":
        emoji = entry.meta.get("emoji", "💎")
        return emoji

    # Для отмены реакции показываем ↩️ + эмодзи
    if entry.operation_type == "reaction_revert":
        emoji = entry.meta.get("emoji", "↩️")
        return f"↩️{emoji}"

    # Для налога
    if entry.operation_type == "tax":
        return "🧾"

    # Для перевода
    if entry.operation_type == "transfer":
        return "💸"

    # По умолчанию
    return OPERATION_ICONS.get(entry.operation_type, "📝")


def _get_action_description(entry) -> str | None:
    """Получить описание действия для операции"""
    if entry.operation_subtype:
        return ACTION_ICONS.get(entry.operation_subtype, entry.operation_subtype)
    return None


def _format_initiator(entry, current_user_id: int) -> str | None:
    """
    Форматировать информацию об инициаторе.
    Возвращает None если инициатор = текущий пользователь или неизвестен.
    """
    if not entry.initiator_user_id or entry.initiator_user_id == current_user_id:
        return None

    username = entry.initiator_username
    if username:
        return f"@{username}"

    return None


def _group_entries_by_source(entries):
    """
    Группирует записи по source_id для отображения связанных операций.
    Возвращает список кортежей (main_entry, related_entries).
    """
    # Словарь для группировки: source_id -> список записей
    grouped = {}
    ungrouped = []

    for entry in entries:
        source_id = entry.source_id
        if source_id is not None:
            if source_id not in grouped:
                grouped[source_id] = []
            grouped[source_id].append(entry)
        else:
            ungrouped.append(entry)

    result = []
    processed_entries = set()

    # Обрабатываем сгруппированные записи
    for _source_id, source_entries in grouped.items():
        # Находим основную запись (transfer) и связанные (tax)
        transfers = [e for e in source_entries if e.operation_type == "transfer"]
        taxes = [e for e in source_entries if e.operation_type == "tax"]

        # Для каждой записи о переводе добавляем связанные налоги
        for transfer in transfers:
            related = [t for t in taxes if t.initiator_user_id == transfer.initiator_user_id]
            result.append((transfer, related))
            processed_entries.add(id(transfer))
            for t in related:
                processed_entries.add(id(t))

        # Оставшиеся налоги (без перевода) добавляем как отдельные
        for tax in taxes:
            if id(tax) not in processed_entries:
                result.append((tax, []))
                processed_entries.add(id(tax))

        # Остальные записи (реакции и т.д.) добавляем по отдельности
        for entry in source_entries:
            if id(entry) not in processed_entries:
                result.append((entry, []))
                processed_entries.add(id(entry))

    # Добавляем несгруппированные записи
    for entry in ungrouped:
        result.append((entry, []))

    # Сортируем все записи по created_at DESC
    result.sort(key=lambda x: x[0].created_at, reverse=True)

    return result


def render_personal_stats(
    dto: PersonalStatsDTO,
    current_user_id: int | None = None,
    user_timezone: str = "UTC",
) -> str:
    """
    Рендеринг личной статистики.

    Формат:
    📊 Твоя статистика
    💰 Баланс: 1000

    24.02 14:30 💎 +50 от @username
    24.02 12:00 💸 -100 перевод
    """
    header = ["📊 *Твоя статистика*"]
    if dto.chat_title:
        header.append(f"💬 Чат: *{dto.chat_title}*")
    header.append(f"💰 Баланс: *{dto.balance}*")
    header.append("")

    lines: list[str] = header

    if not dto.entries:
        lines.append("Пока нет операций.")
        return "\n".join(lines)

    # Группируем записи по source_id
    grouped = _group_entries_by_source(dto.entries)

    for main_entry, related_entries in grouped:
        # Конвертируем время в локальный часовой пояс пользователя
        local_dt = _convert_to_timezone(main_entry.created_at, user_timezone)

        # Форматируем дату и время
        date = local_dt.strftime("%d.%m %H:%M")

        # Иконка операции
        icon = _get_operation_icon(main_entry)

        # Сумма со знаком
        sign = "+" if main_entry.amount > 0 else "−"
        amount = abs(main_entry.amount)

        # Инициатор (если не сам пользователь)
        initiator = _format_initiator(main_entry, current_user_id or main_entry.user_id)

        # Для перевода добавляем информацию о получателе/отправителе
        extra_info = ""
        if main_entry.operation_type == "transfer":
            if main_entry.amount < 0:
                # Отправка перевода
                recipient_id = main_entry.meta.get("recipient_user_id")
                if recipient_id:
                    extra_info = " ↪️ пользователю"
            else:
                # Получение перевода
                sender_id = main_entry.meta.get("from_user_id")
                if sender_id:
                    extra_info = " ↩️ от пользователя"

        # Формируем строку
        if initiator:
            lines.append(f"{date} {icon} {sign}{amount}{extra_info} от {initiator}")
        else:
            lines.append(f"{date} {icon} {sign}{amount}{extra_info}")

        # Добавляем связанные записи (налоги)
        for related in related_entries:
            tax_dt = _convert_to_timezone(related.created_at, user_timezone)
            tax_date = tax_dt.strftime("%d.%m")
            tax_sign = "+" if related.amount > 0 else "−"
            tax_amount = abs(related.amount)
            lines.append(f"                    🧾 {tax_sign}{tax_amount} налог")

    return "\n".join(lines)


def _convert_to_timezone(dt: datetime, tz: str) -> datetime:
    """
    Конвертировать datetime из UTC в указанный часовой пояс.

    Args:
        dt: datetime в UTC
        tz: Название часового пояса (например, "Europe/Moscow")

    Returns:
        datetime в локальном часовом поясе
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Если datetime без timezone, считаем что это UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Проверяем, что tz это валидный часовой пояс
    if not tz or tz == "UTC":
        return dt

    try:
        from zoneinfo import ZoneInfo

        target_tz = ZoneInfo(tz)
        result = dt.astimezone(target_tz)
        logger.debug(f"Timezone conversion: {dt} ({tz}) -> {result}")
        return result
    except Exception as e:
        # При ошибке возвращаем UTC
        logger.warning(f"Failed to convert timezone {tz}: {e}. Using UTC.")
        return dt
