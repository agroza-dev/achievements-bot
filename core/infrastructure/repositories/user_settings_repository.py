"""
Репозиторий для работы с настройками пользователей.

Работает с таблицей user_settings.
"""

import json
import logging
from typing import Any

import asyncpg

from core.dto.user_settings_dto import UserSettingsDTO, UserSettingsHistoryDTO

logger = logging.getLogger(__name__)


class UserSettingsRepository:
    """
    Репозиторий для работы с настройками пользователя.

    Использует отдельную таблицу для настроек.
    """

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_settings(self, user_id: int) -> UserSettingsDTO | None:
        """
        Получить настройки пользователя.

        Args:
            user_id: Внутренний ID пользователя

        Returns:
            UserSettingsDTO или None если настройки не найдены
        """
        query = """
            SELECT
                user_id,
                notifications_enabled,
                created_at,
                updated_at,
                updated_by_user_id
            FROM user_settings
            WHERE user_id = $1
        """
        record = await self.conn.fetchrow(query, user_id)
        return self._map_settings(record) if record else None

    async def get_settings_sync(self, user_id: int) -> UserSettingsDTO | None:
        """
        Получить настройки пользователя (синхронная версия).

        Args:
            user_id: Внутренний ID пользователя

        Returns:
            UserSettingsDTO или None если настройки не найдены
        """
        query = """
            SELECT
                user_id,
                notifications_enabled,
                created_at,
                updated_at,
                updated_by_user_id
            FROM user_settings
            WHERE user_id = $1
        """
        record = await self.conn.fetchrow(query, user_id)
        return self._map_settings(record) if record else None

    async def get_or_create_settings(self, user_id: int) -> UserSettingsDTO:
        """
        Получить или создать настройки пользователя.

        Args:
            user_id: Внутренний ID пользователя

        Returns:
            UserSettingsDTO
        """
        # Пробуем получить
        settings = await self.get_settings(user_id)
        if settings:
            return settings

        # Создаём новые
        query = """
            INSERT INTO user_settings (user_id)
            VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
            RETURNING
                user_id,
                notifications_enabled,
                created_at,
                updated_at,
                updated_by_user_id
        """
        record = await self.conn.fetchrow(query, user_id)
        return self._map_settings(record)

    async def update_settings(
        self,
        user_id: int,
        **kwargs: Any,
    ) -> UserSettingsDTO | None:
        """
        Обновить настройки пользователя.

        Args:
            user_id: Внутренний ID пользователя
            **kwargs: Поля для обновления (например: notifications_enabled=True)

        Returns:
            Обновлённые UserSettingsDTO или None
        """
        if not kwargs:
            return await self.get_settings(user_id)

        # Фильтруем разрешённые поля
        allowed_fields = {
            'notifications_enabled',
            'updated_by_user_id',
        }
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not filtered_kwargs:
            logger.warning(f"Попытка обновить недопустимые поля: {kwargs.keys()}")
            return await self.get_settings(user_id)

        # Логируем изменения
        await self._log_changes(user_id, filtered_kwargs)

        # Строим динамический запрос
        set_clauses = []
        values = [user_id]
        param_idx = 2

        for field_name, value in filtered_kwargs.items():
            set_clauses.append(f"{field_name} = ${param_idx}")
            values.append(value)
            param_idx += 1

        query = f"""
            UPDATE user_settings
            SET {', '.join(set_clauses)}
            WHERE user_id = $1
            RETURNING
                user_id,
                notifications_enabled,
                created_at,
                updated_at,
                updated_by_user_id
        """
        record = await self.conn.fetchrow(query, *values)
        return self._map_settings(record) if record else None

    async def _log_changes(
        self,
        user_id: int,
        new_values: dict[str, Any],
        changed_by_user_id: int | None = None,
    ) -> None:
        """
        Записать историю изменений.

        Args:
            user_id: Внутренний ID пользователя
            new_values: Новые значения полей
            changed_by_user_id: Кто изменил
        """
        # Получаем текущие значения
        current = await self.get_settings(user_id)

        for field_name, new_value in new_values.items():
            old_value = getattr(current, field_name, None) if current else None

            # Пропускаем если значение не изменилось
            if old_value == new_value:
                continue

            query = """
                INSERT INTO user_settings_history
                    (user_id, setting_name, old_value, new_value, changed_by_user_id)
                VALUES ($1, $2, $3, $4, $5)
            """
            await self.conn.execute(
                query,
                user_id,
                field_name,
                self._to_jsonb(old_value),
                self._to_jsonb(new_value),
                changed_by_user_id,
            )

    @staticmethod
    def _to_jsonb(value: Any) -> str | None:
        """Преобразовать значение в JSONB формат (JSON строка)."""
        if value is None:
            return None
        return json.dumps({"value": value})

    @staticmethod
    def _map_settings(record: asyncpg.Record) -> UserSettingsDTO:
        """Преобразовать запись БД в DTO."""
        return UserSettingsDTO(
            user_id=record["user_id"],
            notifications_enabled=record["notifications_enabled"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            updated_by_user_id=record["updated_by_user_id"],
        )

    async def get_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UserSettingsHistoryDTO]:
        """
        Получить историю изменений настроек пользователя.

        Args:
            user_id: Внутренний ID пользователя
            limit: Максимальное количество записей
            offset: Смещение

        Returns:
            Список записей истории
        """
        query = """
            SELECT
                id,
                user_id,
                setting_name,
                old_value,
                new_value,
                changed_by_user_id,
                changed_at
            FROM user_settings_history
            WHERE user_id = $1
            ORDER BY changed_at DESC
            LIMIT $2 OFFSET $3
        """
        rows = await self.conn.fetch(query, user_id, limit, offset)
        return [self._map_history(row) for row in rows]

    @staticmethod
    def _map_history(record: asyncpg.Record) -> UserSettingsHistoryDTO:
        """Преобразовать запись БД в DTO истории."""
        return UserSettingsHistoryDTO(
            id=record["id"],
            user_id=record["user_id"],
            setting_name=record["setting_name"],
            old_value=record["old_value"],
            new_value=record["new_value"],
            changed_by_user_id=record["changed_by_user_id"],
            changed_at=record["changed_at"],
        )
