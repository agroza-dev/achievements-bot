from sqlalchemy import JSON, BigInteger, Column, DateTime, Index, Table, UniqueConstraint, func

from core.models.metadata import metadata

bot_persistence = Table(
    "bot_persistence",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=False),
    Column("chat_id", BigInteger, nullable=True),
    Column("user_id", BigInteger, nullable=True),
    Column("bot_data", JSON, nullable=True),
    Column("chat_data", JSON, nullable=True),
    Column("user_data", JSON, nullable=True),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    UniqueConstraint("chat_id", "user_id", name="uq_chat_id_user_id"),
    Index("idx_bot_persistence_chat_id", "chat_id"),
    Index("idx_bot_persistence_user_id", "user_id"),
)
