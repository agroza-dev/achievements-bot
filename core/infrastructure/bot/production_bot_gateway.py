"""Production реализация BotGateway с использованием telegram.Bot."""

from typing import Any

from telegram import Bot

from core.ports.bot_gateway import BotGateway


class ProductionBotGateway(BotGateway):
    """
    Production реализация BotGateway.

    Обёртка над telegram.Bot для реального взаимодействия с Telegram API.
    """

    def __init__(self, bot: Bot):
        """
        Инициализация gateway.

        Args:
            bot: Экземпляр telegram.Bot
        """
        self._bot = bot

    async def send_message(self, chat_id: int, text: str, **kwargs: Any) -> dict[str, Any]:
        """Отправить сообщение в чат."""
        message = await self._bot.send_message(chat_id=chat_id, text=text, **kwargs)
        return {
            "message_id": message.message_id,
            "chat_id": message.chat_id,
            "text": message.text,
            "from_user_id": message.from_user.id if message.from_user else None,
        }

    async def set_message_reaction(
        self,
        chat_id: int,
        message_id: int,
        reaction: str | list[str],
        **kwargs: Any,
    ) -> bool:
        """Установить реакцию на сообщение."""
        from telegram import ReactionTypeEmoji

        # Преобразуем строку или список строк в список ReactionTypeEmoji
        if isinstance(reaction, str):
            reactions = [ReactionTypeEmoji(emoji=reaction)]
        else:
            reactions = [ReactionTypeEmoji(emoji=emoji) for emoji in reaction]

        is_big = kwargs.get("is_big", False)
        await self._bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=reactions,
            is_big=is_big,
        )
        return True

    async def get_chat(self, chat_id: int) -> dict[str, Any]:
        """Получить информацию о чате."""
        chat = await self._bot.get_chat(chat_id=chat_id)
        return {
            "id": chat.id,
            "type": chat.type,
            "title": chat.title,
            "username": chat.username,
            "description": chat.description,
        }

    async def get_chat_member(self, chat_id: int, user_id: int) -> dict[str, Any]:
        """Получить информацию о пользователе в чате."""
        member = await self._bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return {
            "user_id": member.user.id,
            "username": member.user.username,
            "first_name": member.user.first_name,
            "last_name": member.user.last_name,
            "status": member.status,
            "is_bot": member.user.is_bot,
        }

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        **kwargs: Any,
    ) -> bool:
        """Ответить на callback query."""
        return await self._bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text=text,
            **kwargs,
        )
