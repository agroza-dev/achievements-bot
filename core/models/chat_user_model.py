from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, Table, func
from sqlalchemy.schema import ForeignKey, UniqueConstraint

from core.models.metadata import metadata

chat_users = Table(
    "chat_users",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("chat_id", BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("is_admin", Boolean, nullable=False, server_default="false"),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("rating", Integer, nullable=True, server_default="0"),
    Column("joined_at", DateTime(timezone=True), server_default=func.now()),
    UniqueConstraint("chat_id", "user_id", name="uq_chat_user"),
)
