from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Table, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import text

from core.models.metadata import metadata

chat_messages = Table(
    "chat_messages",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("chat_id", BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
    Column("tg_message_id", BigInteger, nullable=False),
    Column("author_user_id", BigInteger, ForeignKey("users.id", ondelete="SET NULL")),
    Column("message_type", String(32), nullable=False),
    Column("message_meta", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("stored_at", DateTime(timezone=True), server_default=func.now()),
    UniqueConstraint("chat_id", "tg_message_id", name="uq_chat_message"),
)
