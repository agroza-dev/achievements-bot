"""
Репозиторий для работы с настройками чатов (v2).

Работает с таблицей chat_settings.
"""

import logging
from typing import Any

import asyncpg

from core.dto.chat_settings_dto import ChatSettingsDTO, ChatSettingsHistoryDTO

logger = logging.getLogger(__name__)


class ChatSettingsRepository:
    """
    Репозиторий для работы с настройками чата.

    Использует отдельную таблицу вместо JSONB поля.
    """

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_settings(self, chat_id: int) -> ChatSettingsDTO | None:
        """
        Получить настройки чата.

        Args:
            chat_id: Внутренний ID чата

        Returns:
            ChatSettingsDTO или None если настройки не найдены
        """
        query = """
            SELECT
                chat_id,
                periodic_award_enabled,
                periodic_award_amount,
                tax_enabled,
                tax_rate,
                created_at,
                updated_at,
                updated_by_user_id
            FROM chat_settings
            WHERE chat_id = $1
        """
        record = await self.conn.fetchrow(query, chat_id)
        return self._map_settings(record) if record else None

    async def get_settings_sync(self, chat_id: int) -> ChatSettingsDTO | None:
        """
        Получить настройки чата (синхронная версия).

        Args:
            chat_id: Внутренний ID чата

        Returns:
            ChatSettingsDTO или None если настройки не найдены
        """
        query = """
            SELECT
                chat_id,
                periodic_award_enabled,
                periodic_award_amount,
                tax_enabled,
                tax_rate,
                created_at,
                updated_at,
                updated_by_user_id
            FROM chat_settings
            WHERE chat_id = $1
        """
        record = await self.conn.fetchrow(query, chat_id)
        return self._map_settings(record) if record else None

    async def get_or_create_settings(self, chat_id: int) -> ChatSettingsDTO:
        """
        Получить или создать настройки чата.

        Args:
            chat_id: Внутренний ID чата

        Returns:
            ChatSettingsDTO
        """
        # Пробуем получить
        settings = await self.get_settings(chat_id)
        if settings:
            return settings

        # Создаём новые
        query = """
            INSERT INTO chat_settings (chat_id)
            VALUES ($1)
            ON CONFLICT (chat_id) DO NOTHING
            RETURNING
                chat_id,
                periodic_award_enabled,
                periodic_award_amount,
                tax_enabled,
                tax_rate,
                created_at,
                updated_at,
                updated_by_user_id
        """
        record = await self.conn.fetchrow(query, chat_id)
        return self._map_settings(record)

    async def update_settings(
        self,
        chat_id: int,
        **kwargs: Any,
    ) -> ChatSettingsDTO | None:
        """
        Обновить настройки чата.

        Args:
            chat_id: Внутренний ID чата
            **kwargs: Поля для обновления (например: periodic_award_enabled=True)

        Returns:
            Обновлённые ChatSettingsDTO или None
        """
        if not kwargs:
            return await self.get_settings(chat_id)

        # Фильтруем разрешённые поля
        allowed_fields = {
            'periodic_award_enabled',
            'periodic_award_amount',
            'tax_enabled',
            'tax_rate',
            'updated_by_user_id',
        }
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not filtered_kwargs:
            logger.warning(f"Попытка обновить недопустимые поля: {kwargs.keys()}")
            return await self.get_settings(chat_id)

        # Логируем изменения
        await self._log_changes(chat_id, filtered_kwargs)

        # Строим динамический запрос
        set_clauses = []
        values = [chat_id]
        param_idx = 2

        for field_name, value in filtered_kwargs.items():
            set_clauses.append(f"{field_name} = ${param_idx}")
            values.append(value)
            param_idx += 1

        query = f"""
            UPDATE chat_settings
            SET {', '.join(set_clauses)}
            WHERE chat_id = $1
            RETURNING
                chat_id,
                periodic_award_enabled,
                periodic_award_amount,
                tax_enabled,
                tax_rate,
                created_at,
                updated_at,
                updated_by_user_id
        """
        record = await self.conn.fetchrow(query, *values)
        return self._map_settings(record) if record else None

    async def _log_changes(
        self,
        chat_id: int,
        new_values: dict[str, Any],
        changed_by_user_id: int | None = None,
    ) -> None:
        """
        Записать историю изменений.

        Args:
            chat_id: Внутренний ID чата
            new_values: Новые значения полей
            changed_by_user_id: Кто изменил
        """
        # Получаем текущие значения
        current = await self.get_settings(chat_id)

        for field_name, new_value in new_values.items():
            old_value = getattr(current, field_name, None) if current else None

            # Пропускаем если значение не изменилось
            if old_value == new_value:
                continue

            query = """
                INSERT INTO chat_settings_history
                    (chat_id, setting_name, old_value, new_value, changed_by_user_id)
                VALUES ($1, $2, $3, $4, $5)
            """
            await self.conn.execute(
                query,
                chat_id,
                field_name,
                self._to_jsonb(old_value),
                self._to_jsonb(new_value),
                changed_by_user_id,
            )

    @staticmethod
    def _to_jsonb(value: Any) -> dict | None:
        """Преобразовать значение в JSONB формат."""
        if value is None:
            return None
        return {"value": value}

    @staticmethod
    def _map_settings(record: asyncpg.Record) -> ChatSettingsDTO:
        """Преобразовать запись БД в DTO."""
        return ChatSettingsDTO(
            chat_id=record["chat_id"],
            periodic_award_enabled=record["periodic_award_enabled"],
            periodic_award_amount=record["periodic_award_amount"],
            tax_enabled=record["tax_enabled"],
            tax_rate=float(record["tax_rate"]),
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            updated_by_user_id=record["updated_by_user_id"],
        )

    async def get_history(
        self,
        chat_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatSettingsHistoryDTO]:
        """
        Получить историю изменений настроек чата.

        Args:
            chat_id: Внутренний ID чата
            limit: Максимальное количество записей
            offset: Смещение

        Returns:
            Список записей истории
        """
        query = """
            SELECT
                id,
                chat_id,
                setting_name,
                old_value,
                new_value,
                changed_by_user_id,
                changed_at
            FROM chat_settings_history
            WHERE chat_id = $1
            ORDER BY changed_at DESC
            LIMIT $2 OFFSET $3
        """
        rows = await self.conn.fetch(query, chat_id, limit, offset)
        return [self._map_history(row) for row in rows]

    @staticmethod
    def _map_history(record: asyncpg.Record) -> ChatSettingsHistoryDTO:
        """Преобразовать запись БД в DTO истории."""
        return ChatSettingsHistoryDTO(
            id=record["id"],
            chat_id=record["chat_id"],
            setting_name=record["setting_name"],
            old_value=record["old_value"],
            new_value=record["new_value"],
            changed_by_user_id=record["changed_by_user_id"],
            changed_at=record["changed_at"],
        )
