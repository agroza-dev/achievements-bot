import logging
from datetime import UTC, datetime

from core.dto.personal_stats_dto import PersonalStatsDTO

logger = logging.getLogger(__name__)

# Иконки для типов операций
OPERATION_ICONS = {
    "reaction": "💎",      # реакция на сообщение
    "reaction_revert": "↩️",  # отмена реакции
    "tax": "🧾",          # налог
    "transfer": "💸",     # перевод между пользователями
    "bonus": "🎁",        # бонус
    "award": "🎁",        # системное зачисление (periodic_award, one_time_award)
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

    # Для бонуса
    if entry.operation_type == "bonus":
        return "🎁"

    # По умолчанию
    return OPERATION_ICONS.get(entry.operation_type, "📝")


def _get_action_description(entry) -> str | None:
    """Получить описание действия для операции"""
    logger.info(
        "[ACTION_DESC] operation_type=%s, operation_subtype=%s, meta=%s",
        entry.operation_type,
        entry.operation_subtype,
        entry.meta,
    )

    # Для бонуса показываем тип бонуса
    if entry.operation_type == "bonus":
        subtype = entry.operation_subtype
        if subtype == "welcome":
            logger.info("[ACTION_DESC] bonus/welcome -> приветственный бонус")
            return "приветственный бонус"
        if subtype == "award":
            logger.info("[ACTION_DESC] bonus/award -> еженедельное зачисление")
            return "еженедельное зачисление"
        logger.info(f"[ACTION_DESC] bonus/{subtype} -> {subtype}")
        return subtype

    # Для award (periodic_award, one_time_award) показываем описание с комментарием
    if entry.operation_type == "award":
        subtype = entry.operation_subtype
        comment = entry.meta.get("comment", "") if entry.meta else ""

        logger.info(
            "[ACTION_DESC] award subtype=%s, comment=%s",
            subtype,
            comment,
        )

        if subtype == "periodic_award":
            logger.info("[ACTION_DESC] award/periodic_award -> периодическое зачисление")
            return "периодическое зачисление"
        if subtype == "one_time_award":
            if comment:
                logger.info(f"[ACTION_DESC] award/one_time_award с комментарием -> разовое зачисление ({comment})")
                return f"разовое зачисление ({comment})"
            logger.info("[ACTION_DESC] award/one_time_award без комментария -> разовое зачисление")
            return "разовое зачисление"
        logger.info(f"[ACTION_DESC] award/{subtype} -> {subtype}")
        return subtype

    if entry.operation_subtype:
        result = ACTION_ICONS.get(entry.operation_subtype, entry.operation_subtype)
        logger.info("[ACTION_DESC] default subtype=%s -> %s", entry.operation_subtype, result)
        return result
    logger.info("[ACTION_DESC] no subtype -> None")
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

    Если налог (tax) есть, но связанный трансфер не попал в выборку,
    налог не показывается (так как бессмысленен без основного трансфера).
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

        # Если есть налоги, но нет трансферов в выборке - пропускаем их
        # (трансфер не попал в лимит, а налог без него бессмысленен)
        if taxes and not transfers:
            logger.info(
                "[GROUP] Skipping tax entries without transfer for source_id=%s "
                "(transfer not in selection)",
                _source_id,
            )
            for tax in taxes:
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
    📊 Выписка по балансу
    💰 Баланс: 1000

    24.02 14:30 💎 +50 от @username
    24.02 12:00 💸 -100 перевод
    """
    logger.info("[RENDER] Starting render for user_id=%s, entries_count=%s", current_user_id, len(dto.entries) if dto.entries else 0)

    header = ["📊 Выписка по балансу", f"💰 Баланс: {dto.balance}", ""]

    lines: list[str] = header

    if not dto.entries:
        lines.append("Пока нет операций.")
        return "\n".join(lines)

    # Группируем записи по source_id
    grouped = _group_entries_by_source(dto.entries)

    logger.info("[RENDER] Grouped entries: %s groups", len(grouped))

    for main_entry, _related_entries in grouped:
        # Логируем каждую запись для отладки
        logger.info(
            "[RENDER] Entry: type=%s, subtype=%s, amount=%s, meta=%s",
            main_entry.operation_type,
            main_entry.operation_subtype,
            main_entry.amount,
            main_entry.meta,
        )
        # Конвертируем время в локальный часовой пояс пользователя
        local_dt = _convert_to_timezone(main_entry.created_at, user_timezone)

        # Форматируем дату и время
        date = local_dt.strftime("%d.%m %H:%M")

        # Иконка операции
        icon = _get_operation_icon(main_entry)

        # Для перевода формируем сообщение по новому формату
        if main_entry.operation_type == "transfer":
            # Определяем, является ли текущий пользователь инициатором трансфера
            is_initiator = (main_entry.user_id == main_entry.initiator_user_id)

            counterparty_username = main_entry.counterparty_username
            # direction хранится в operation_subtype
            direction = main_entry.operation_subtype or ""
            tax_amount = abs(main_entry.tax) if main_entry.tax else 0
            amount = abs(main_entry.amount)

            logger.debug(
                "Transfer entry: user_id=%s, initiator_user_id=%s, is_initiator=%s, "
                "amount=%s, direction=%s, tax=%s, counterparty=%s",
                main_entry.user_id,
                main_entry.initiator_user_id,
                is_initiator,
                main_entry.amount,
                direction,
                main_entry.tax,
                counterparty_username,
            )

            if is_initiator:
                # Инициатор трансфера
                counterparty = f"@{counterparty_username}" if counterparty_username else "пользователю"

                if direction == "negative":
                    # Отрицательный трансфер (штраф)
                    # Формат: "штраф для @user удержано 100 + налог 10"
                    tax_info = f" + налог {tax_amount}" if tax_amount > 0 else ""
                    lines.append(f"{date} {icon} штраф для {counterparty} удержано {amount}{tax_info}")
                else:
                    # Положительный трансфер
                    # Формат: "трансфер для @user списано 100 + налог 10"
                    tax_info = f" + налог {tax_amount}" if tax_amount > 0 else ""
                    lines.append(f"{date} {icon} трансфер для {counterparty} списано {amount}{tax_info}")
            else:
                # Получатель трансфера
                initiator_username = main_entry.initiator_username
                initiator = f"@{initiator_username}" if initiator_username else "пользователя"

                if direction == "negative":
                    # Отрицательный трансфер (штраф)
                    # Формат: "штраф от @user списано 100"
                    lines.append(f"{date} {icon} штраф от {initiator} списано {amount}")
                else:
                    # Положительный трансфер
                    # Формат: "трансфер от @user начислено 100"
                    lines.append(f"{date} {icon} трансфер от {initiator} начислено {amount}")

            # Налоги уже учтены в основной строке для отправителя
            # Для получателя налоги не показываем
            continue

        # Сумма со знаком
        sign = "+" if main_entry.amount > 0 else "−"
        amount = abs(main_entry.amount)

        # Инициатор (если не сам пользователь)
        initiator = _format_initiator(main_entry, current_user_id or main_entry.user_id)

        # Для бонуса и award добавляем описание
        action_desc = None
        if main_entry.operation_type in ("bonus", "award"):
            action_desc = _get_action_description(main_entry)

        # Формируем строку
        if initiator:
            lines.append(f"{date} {icon} {sign}{amount} от {initiator}")
        elif action_desc:
            lines.append(f"{date} {icon} {sign}{amount} {action_desc}")
        else:
            lines.append(f"{date} {icon} {sign}{amount}")

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
        dt = dt.replace(tzinfo=UTC)

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
