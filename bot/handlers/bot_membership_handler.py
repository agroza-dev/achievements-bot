import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.container import Container

logger = logging.getLogger(__name__)


async def bot_membership_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    logger.info(f"Received bot_membership_handler message: {message}")
    if not message or not message.new_chat_members:
        return

    # Получаем контейнер
    container: Container = context.bot_data["container"]

    # Получаем ID бота
    bot_id = context.bot.id

    if not any(m.id == bot_id for m in message.new_chat_members):
        return

    use_case = container.get_bot_added_to_chat_use_case()
    bots = [user for user in message.new_chat_members if user.is_bot]

    logger.debug(f"Chat {message.chat}")
    logger.debug(f"From user {message.from_user}")
    logger.debug(f"Bots {bots}")

    for bot in bots:
        await use_case.execute(
            tg_chat=message.chat,
            bot=bot,
            added_by=message.from_user,
        )

        # Формируем сообщение в зависимости от типа чата
        is_supergroup = message.chat.type == "supergroup"

        bot_name = context.bot.username

        # Формируем список требований
        requirements = [
            f"Написать команду /start в личные сообщения @{bot_name} — так бот сможет отправлять уведомления и личную статистику",
            "Дождаться, пока активные участники напишут сообщения в чат — бот должен их «увидеть»",
        ]
        if not is_supergroup:
            requirements.append("Преобразовать группу в супергруппу — это нужно для учёта реакций на сообщения")

        # Формируем список доступных функций
        features = [
            "🔄 **Трансферы очков** — переводите очки между участниками в ответ на сообщение или через упоминание",
            "📊 **Статистика** — личная и групповая статистика доступна в личном чате с ботом",
            "🏆 **Таблица лидеров** — узнайте, кто в чате самый активный",
            #"👥 **Группы участников** — создавайте группы (например, «Собаки», «Дизайнеры») и упоминайте их одной командой", TODO нужно реализовать
        ]

        # Собираем сообщение
        text = f"🤖 **{bot_name} добавлен в группу!**\n\n"
        text += "✅ **Что нужно сделать для корректной работы:**\n"
        for i, req in enumerate(requirements, 1):
            text += f"{i}. {req}\n"

        text += "\n🎯 **Доступные функции:**\n"
        text += "\n".join(features)

        text += "\n\n💡 Используйте `/help` для подробной информации о командах"

        await update.message.reply_text(text, parse_mode="Markdown")
        logger.info(
            f"Bot added to chat {message.chat.title} by {message.from_user.username}",
            extra={
                "tg_chat_id": message.chat.id,
                "added_by": message.from_user.id if message.from_user else None,
            }
        )
