"""Интеграционные тесты для репозиториев с PostgreSQL через testcontainers."""

import pytest
from telegram import User

from core.infrastructure.repositories.user_repository import UserRepository


@pytest.mark.integration
class TestUserRepository:
    """Интеграционные тесты UserRepository."""

    @pytest.fixture
    def user_repo(self, db_connection):
        """Создать UserRepository с тестовым подключением."""
        return UserRepository(db_connection)

    @pytest.mark.asyncio
    async def test_upsert_and_get_by_tg_id(self, user_repo: UserRepository):
        """Тест: создание и получение пользователя."""
        tg_user = User(id=123456, is_bot=False, first_name="Test", username="testuser")

        # Создаём пользователя
        dto = await user_repo.upsert(tg_user)

        assert dto.tg_id == 123456
        assert dto.username == "testuser"
        assert dto.first_name == "Test"

        # Получаем пользователя
        found = await user_repo.get_by_tg_id(123456)

        assert found is not None
        assert found.tg_id == 123456
        assert found.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_by_tg_id_not_found(self, user_repo: UserRepository):
        """Тест: получение несуществующего пользователя."""
        found = await user_repo.get_by_tg_id(999999)
        assert found is None

    @pytest.mark.asyncio
    async def test_upsert_update_existing(self, user_repo: UserRepository):
        """Тест: обновление существующего пользователя."""
        # Создаём
        tg_user = User(id=111, is_bot=False, first_name="First", username="first")
        await user_repo.upsert(tg_user)

        # Обновляем
        tg_user_updated = User(id=111, is_bot=False, first_name="Updated", username="updated")
        dto = await user_repo.upsert(tg_user_updated)

        assert dto.first_name == "Updated"
        assert dto.username == "updated"

        # Проверяем что обновился
        found = await user_repo.get_by_tg_id(111)
        assert found.first_name == "Updated"
        assert found.username == "updated"

    @pytest.mark.asyncio
    async def test_get_id_by_tg_id(self, user_repo: UserRepository):
        """Тест: получение внутреннего ID пользователя."""
        tg_user = User(id=222, is_bot=False, first_name="ID Test", username="idtest")
        await user_repo.upsert(tg_user)

        internal_id = await user_repo.get_id_by_tg_id(222)
        assert internal_id is not None
        assert isinstance(internal_id, int)

    @pytest.mark.asyncio
    async def test_get_id_by_tg_id_not_found(self, user_repo: UserRepository):
        """Тест: получение ID несуществующего пользователя."""
        internal_id = await user_repo.get_id_by_tg_id(999999)
        assert internal_id is None

    @pytest.mark.asyncio
    async def test_get_by_internal_id(self, user_repo: UserRepository):
        """Тест: получение пользователя по-внутреннему ID."""
        tg_user = User(id=333, is_bot=False, first_name="Internal", username="internal")
        created = await user_repo.upsert(tg_user)

        found = await user_repo.get_by_internal_id(created.id)

        assert found is not None
        assert found.tg_id == 333
        assert found.username == "internal"

    @pytest.mark.asyncio
    async def test_upsert_bot(self, user_repo: UserRepository):
        """Тест: создание бота."""
        dto = await user_repo.upsert_bot(
            bot_id=444,
            username="botuser",
            first_name="Bot User",
            last_name="",
            added_by=123,
        )

        assert dto.tg_id == 444
        assert dto.username == "botuser"
        assert dto.is_bot is True

        found = await user_repo.get_by_tg_id(444)
        assert found is not None
        assert found.is_bot is True
