import logging

from telegram import Chat

from core.infrastructure.repositories.chat_repository import ChatRepository

logger = logging.getLogger(__name__)


class MigrateChatUseCase:
    """
    UseCase для миграции чата при превращении группы в супергруппу.

    При конвертации группы в супергруппу Telegram меняет идентификатор чата.
    Этот UseCase обновляет tg_id в базе данных, сохраняя все связанные данные:
    - пользователей чата
    - сообщения
    - реакции
    - историю рейтинга
    """

    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    async def execute(self, *, old_chat: Chat, new_chat: Chat):
        """
        Выполнить миграцию чата.

        Args:
            old_chat: Чат со старым tg_id (группа)
            new_chat: Чат с новым tg_id (супергруппа)
        """
        async with self.uow_factory() as uow:
            chat_repo: ChatRepository = uow.get_repo(ChatRepository)


            old_tg_id = old_chat.id
            new_tg_id = new_chat.id

            logger.info(
                f"Миграция чата: {old_tg_id} -> {new_tg_id}",
                extra={
                    "old_chat_id": old_tg_id,
                    "new_chat_id": new_tg_id,
                    "chat_title": new_chat.title,
                }
            )

            # Проверяем, существует ли уже чат с новым tg_id
            existing_chat = await chat_repo.get_by_tg_id(new_tg_id)
            if existing_chat:
                logger.warning(
                    f"Чат с новым tg_id {new_tg_id} уже существует. Миграция не требуется.",
                    extra={
                        "new_chat_id": new_tg_id,
                        "existing_chat_title": existing_chat.title,
                    }
                )
                return

            # Проверяем, существует ли чат со старым tg_id
            old_chat_exists = await chat_repo.get_by_tg_id(old_tg_id)
            logger.debug(
                f"Проверка старого чата {old_tg_id}: {'найден' if old_chat_exists else 'не найден'}",
                extra={"old_chat_id": old_tg_id}
            )

            if old_chat_exists:
                # Выполняем миграцию - чат найден
                logger.info(
                    f"Выполняем миграцию чата {old_tg_id} -> {new_tg_id}",
                    extra={"old_chat_id": old_tg_id, "new_chat_id": new_tg_id}
                )
                migrated = await chat_repo.migrate_chat(
                    old_tg_id=old_tg_id,
                    new_tg_id=new_tg_id,
                )

                if migrated:
                    logger.info(
                        f"Чат успешно мигрирован: {old_tg_id} -> {new_tg_id}",
                        extra={
                            "old_chat_id": old_tg_id,
                            "new_chat_id": new_tg_id,
                        }
                    )
                else:
                    logger.error(
                        f"Не удалось мигрировать чат {old_tg_id} -> {new_tg_id}. migrate_chat вернул False",
                        extra={"old_chat_id": old_tg_id, "new_chat_id": new_tg_id}
                    )
            else:
                # Чат со старым ID не найден - создаём новый с новым ID
                # Это происходит если группа никогда не была активна в боте до миграции
                logger.info(
                    f"Чат со старым ID {old_tg_id} не найден. Создаём новый чат с ID {new_tg_id}",
                    extra={"old_chat_id": old_tg_id, "new_chat_id": new_tg_id}
                )

                from telegram import Chat as TelegramChat
                new_chat_obj = await chat_repo.upsert(TelegramChat(
                    id=new_tg_id,
                    type=new_chat.type,
                    title=new_chat.title,
                    username=new_chat.username,
                ))

                logger.info(
                    f"Создан новый чат с ID {new_tg_id} (internal id: {new_chat_obj.id})",
                    extra={"new_chat_id": new_tg_id}
                )
