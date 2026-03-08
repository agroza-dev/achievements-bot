import logging

from telegram import Chat

from core.infrastructure.repositories.chat_repository import ChatRepository

logger = logging.getLogger(__name__)


class UpdateChatTitleUseCase:
    """
    UseCase для обновления названия чата.

    Обновляет название чата в базе данных при получении события NEW_CHAT_TITLE.
    """

    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    async def execute(self, *, tg_chat: Chat):
        """
        Обновить название чата.

        Args:
            tg_chat: Telegram чат с новым названием
        """
        async with self.uow_factory() as uow:
            chat_repo: ChatRepository = uow.get_repo(ChatRepository)

            tg_id = tg_chat.id
            new_title = tg_chat.title

            logger.info(
                f"Обновление названия чата {tg_id}: '{new_title}'",
                extra={
                    "chat_id": tg_id,
                    "new_title": new_title,
                }
            )

            # Проверяем, существует ли чат
            chat = await chat_repo.get_by_tg_id(tg_id)
            if not chat:
                logger.warning(
                    f"Чат {tg_id} не найден в базе данных. Название не обновлено.",
                    extra={"chat_id": tg_id}
                )
                return

            # Обновляем название
            updated = await chat_repo.update_title(
                tg_id=tg_id,
                new_title=new_title,
            )

            if updated:
                logger.info(
                    f"Название чата {tg_id} успешно обновлено на '{new_title}'",
                    extra={"chat_id": tg_id, "new_title": new_title}
                )
            else:
                logger.error(
                    f"Не удалось обновить название чата {tg_id}",
                    extra={"chat_id": tg_id}
                )
