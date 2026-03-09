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
            f"Написать команду /start в личные сообщения @{bot_name} — так бот сможет отправлять уведомления и показывать историю изменения баланса",
            "Дождаться, пока активные участники напишут сообщения в чат — бот должен их «увидеть»",
        ]
        if not is_supergroup:
            requirements.append("Преобразовать группу в супергруппу — это нужно для учёта реакций на сообщения")
            requirements.append("Сделать бота админом - это также нужно для учета реакций")

        # Формируем список доступных функций
        features = [
            "🔄 <b>Трансферы очков</b> — переводите очки между участниками в ответ на сообщение или через упоминание. Например: <code>Дарю @user 15</code> или <code>+15</code>",
            f"🏆 <b>Статистика</b> — <code>/leaderboard</code> в чате или личном чате с @{bot_name}",
            f"📊 <b>История</b> баланса — <code>/stats</code> в личном чате с @{bot_name}",
            #"👥 <b>Группы участников</b> — создавайте группы и упоминайте их одной командой", TODO нужно реализовать
        ]

        # Собираем сообщение
        text = f"🤖 <b>{bot_name} добавлен в группу!</b>\n\n"
        text += "✅ <b>Что нужно сделать для корректной работы:</b>\n"
        for i, req in enumerate(requirements, 1):
            text += f"{i}. {req}\n"

        text += "\n🎯 <b>Доступные функции:</b>\n"
        for feature in features:
            text += f"• {feature}\n"

        await update.message.reply_text(text, parse_mode="HTML")
        logger.info(
            f"Bot added to chat {message.chat.title} by {message.from_user.username}",
            extra={
                "tg_chat_id": message.chat.id,
                "added_by": message.from_user.id if message.from_user else None,
            }
        )
