"""Интеграционные тесты для ChatRepository.migrate_chat."""

import pytest
from telegram import Chat

from core.infrastructure.repositories.chat_repository import ChatRepository


@pytest.mark.integration
class TestChatRepositoryMigrate:
    """Интеграционные тесты миграции чатов."""

    @pytest.fixture
    def chat_repo(self, db_connection):
        """Создать ChatRepository с тестовым подключением."""
        return ChatRepository(db_connection)

    @pytest.mark.asyncio
    async def test_migrate_chat_success(self, chat_repo: ChatRepository):
        """Тест: успешная миграция чата."""
        # Создаём старый чат (группа)
        old_chat = Chat(id=-100, type="group", title="Test Chat")
        await chat_repo.upsert(old_chat)

        # Выполняем миграцию
        new_tg_id = -1001234567890
        migrated = await chat_repo.migrate_chat(
            old_tg_id=-100,
            new_tg_id=new_tg_id,
        )

        assert migrated is True

        # Проверяем что старый tg_id больше не существует
        old_found = await chat_repo.get_by_tg_id(-100)
        assert old_found is None

        # Проверяем что новый tg_id существует
        new_found = await chat_repo.get_by_tg_id(new_tg_id)
        assert new_found is not None
        assert new_found.title == "Test Chat"

    @pytest.mark.asyncio
    async def test_migrate_chat_not_found(self, chat_repo: ChatRepository):
        """Тест: миграция несуществующего чата."""
        # Пытаемся мигрировать чат который не существует
        migrated = await chat_repo.migrate_chat(
            old_tg_id=-999,
            new_tg_id=-1001234567890,
        )

        assert migrated is False

    @pytest.mark.asyncio
    async def test_migrate_chat_preserves_settings(self, chat_repo: ChatRepository):
        """Тест: миграция сохраняет настройки чата."""
        # Создаём чат с настройками
        old_chat = Chat(id=-200, type="group", title="Settings Chat")
        await chat_repo.upsert(old_chat)

        # Выполняем миграцию
        new_tg_id = -100222333444
        await chat_repo.migrate_chat(
            old_tg_id=-200,
            new_tg_id=new_tg_id,
        )

        # Получаем новый чат
        new_chat = await chat_repo.get_by_tg_id(new_tg_id)
        assert new_chat is not None
        # Настройки должны сохраниться (пустой dict по умолчанию)
        assert new_chat.settings == {}

    @pytest.mark.asyncio
    async def test_migrate_chat_updates_timestamp(self, chat_repo: ChatRepository):
        """Тест: миграция обновляет updated_at."""
        import asyncio

        # Создаём чат
        old_chat = Chat(id=-300, type="group", title="Timestamp Chat")
        await chat_repo.upsert(old_chat)

        # Ждём немного чтобы timestamp отличался
        await asyncio.sleep(0.1)

        # Получаем старое значение updated_at
        old_record = await chat_repo.get_by_tg_id(-300)
        old_updated_at = old_record.updated_at

        # Выполняем миграцию
        new_tg_id = -100333444555
        await chat_repo.migrate_chat(
            old_tg_id=-300,
            new_tg_id=new_tg_id,
        )

        # Получаем новое значение updated_at
        new_record = await chat_repo.get_by_tg_id(new_tg_id)
        new_updated_at = new_record.updated_at

        # Проверяем что timestamp обновился
        assert new_updated_at >= old_updated_at
