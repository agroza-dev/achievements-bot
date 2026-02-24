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


def render_personal_stats(dto: PersonalStatsDTO, current_user_id: int | None = None) -> str:
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

    for entry in dto.entries:
        # Дата и время
        date = entry.created_at.strftime("%d.%m %H:%M")

        # Иконка операции
        icon = _get_operation_icon(entry)

        # Сумма со знаком
        sign = "+" if entry.amount > 0 else "−"
        amount = abs(entry.amount)

        # Инициатор (если не сам пользователь)
        initiator = _format_initiator(entry, current_user_id or entry.user_id)

        # Формируем строку: дата иконка сумма [от кого]
        if initiator:
            lines.append(f"{date} {icon} {sign}{amount} от {initiator}")
        else:
            lines.append(f"{date} {icon} {sign}{amount}")

    return "\n".join(lines)
