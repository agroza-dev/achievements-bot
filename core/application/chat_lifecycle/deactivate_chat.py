import logging

from telegram import Chat

from core.infrastructure.repositories.chat_repository import ChatRepository

logger = logging.getLogger(__name__)


class DeactivateChatUseCase:
    """Use case для деактивации чата."""

    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    async def execute(
        self,
        *,
        tg_chat: Chat,
        reason: str = "bot_removed",
    ):
        """
        Деактивировать чат.

        Args:
            tg_chat: Чат Telegram
            reason: Причина деактивации ('bot_removed', 'chat_deleted')
        """
        async with self.uow_factory() as uow:
            chat_repo: ChatRepository = uow.get_repo(ChatRepository)

            chat = await chat_repo.get_by_tg_id(tg_chat.id)
            if not chat:
                logger.warning(f"Chat {tg_chat.id} not found for deactivation")
                return

            # Деактивируем чат
            await chat_repo.deactivate(chat.id)

            logger.info(
                f"Chat {tg_chat.title} (id={tg_chat.id}) deactivated. Reason: {reason}",
                extra={
                    "tg_chat_id": tg_chat.id,
                    "reason": reason,
                }
            )
