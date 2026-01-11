from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from core.models.metadata import metadata

rating_ledger = Table(
    "rating_ledger",
    metadata,

    Column("id", BigInteger, primary_key=True, autoincrement=True),

    # Контекст (жёсткая изоляция чатов)
    Column(
        "chat_id",
        BigInteger,
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "user_id",
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),

    # Кто инициировал изменение
    Column(
        "initiator_user_id",
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Кто инициировал операцию (user/system/bot)",
    ),

    # Значение изменения
    Column("amount", Integer, nullable=False),

    # Snapshot после операции (опционально, но очень удобно)
    Column("balance_after", Integer, nullable=True),

    # Тип операции
    Column("operation_type", String(32), nullable=False),
    Column("operation_subtype", String(32), nullable=True),

    # Источник (с чем связана операция)
    Column("source_type", String(32), nullable=False),
    Column("source_id", BigInteger, nullable=True),

    # Расширяемые данные
    Column(
        "meta",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    ),

    # Реверс
    Column(
        "is_reverted",
        Boolean,
        nullable=False,
        server_default=text("false"),
    ),
    Column("reverted_at", DateTime(timezone=True), nullable=True),
    Column(
        "reverted_by_id",
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ),

    # Время
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),

    # Индексы
    Index("idx_rating_ledger_chat_user", "chat_id", "user_id"),
    Index("idx_rating_ledger_source", "source_type", "source_id"),
    Index("idx_rating_ledger_created_at", "created_at"),
)
