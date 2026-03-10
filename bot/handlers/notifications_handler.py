"""
Handler для управления настройками уведомлений пользователя.

Команда: /notifications [on|off]
"""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.container import Container

logger = logging.getLogger(__name__)


async def notifications_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /notifications.

    Использование:
        /notifications on  - включить уведомления
        /notifications off - выключить уведомления
        /notifications     - проверить текущий статус
    """
    user = update.effective_user
    if not user:
        logger.warning("Received notification command without user")
        return

    tg_id = user.id

    # Получаем контейнер
    container: Container = context.bot_data.get("container")
    if not container:
        logger.error("Container not initialized.")
        await update.message.reply_text("❌ Ошибка: бот не инициализирован")
        return

    # Получаем аргумент команды (on/off)
    args = context.args
    action = args[0].lower() if args else None

    if action not in ("on", "off", None):
        await update.message.reply_text(
            "❌ Неверный аргумент. Используйте:\n"
            "<code>/notifications on</code>  - вкл уведомления\n"
            "<code>/notifications off</code> - выкл уведомления\n"
            "/notifications     - проверить статус",
            parse_mode=ParseMode.HTML,
        )
        return

    # Получаем внутренний ID пользователя
    get_or_create_user_uc = container.get_get_or_create_user_use_case()
    try:
        user_id = await get_or_create_user_uc.execute(tg_id=tg_id)
    except Exception as e:
        logger.error(f"Failed to get/create user for tg_id {tg_id}: {e}")
        await update.message.reply_text("❌ Ошибка при получении пользователя. Попробуйте позже.")
        return

    # Получаем use case
    get_settings_uc = container.get_user_settings_use_case()
    update_notifications_uc = container.get_update_user_notifications_use_case()

    if action is None:
        # Просто показываем текущий статус
        settings = await get_settings_uc.execute(user_id=user_id)
        enabled = settings.notifications.enabled

        status_text = "✅ включены" if enabled else "❌ выключены"
        await update.message.reply_text(
            f"🔔 Уведомления: {status_text}\n\n"
            f"Используйте:\n"
            "<code>/notifications on</code>  - вкл уведомления\n"
            "<code>/notifications off</code> - выкл уведомления",
            parse_mode=ParseMode.HTML,
        )
        return

    # Включаем/выключаем уведомления
    enabled = action == "on"
    try:
        await update_notifications_uc.execute(
            user_id=user_id,
            enabled=enabled,
            updated_by_user_id=user_id,
        )

        status_text = "✅ включены" if enabled else "❌ выключены"
        await update.message.reply_text(
            f"🔔 Уведомления {status_text}\n\n"
            f"Теперь бот будет {'присылать' if enabled else 'не присылать'} вам уведомления.\n"
            f"Используйте:\n"
            "<code>/notifications on</code>  - вкл уведомления\n"
            "<code>/notifications off</code> - выкл уведомления",
            parse_mode=ParseMode.HTML,
        )
        logger.info(f"User {user_id} (tg_id={tg_id}) {'enabled' if enabled else 'disabled'} notifications")

    except Exception as e:
        logger.error(f"Failed to update notifications for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обновлении настроек. Попробуйте позже."
        )
