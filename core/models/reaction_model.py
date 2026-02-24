from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Table,
    func,
)

from core.models.metadata import metadata

reactions = Table(
    "reactions",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("chat_id", BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
    Column("message_id", BigInteger, nullable=False),
    Column("from_user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("to_user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("reaction", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    # Составной FK на chat_messages (chat_id, tg_message_id)
    ForeignKeyConstraint(
        ["chat_id", "message_id"],
        ["chat_messages.chat_id", "chat_messages.tg_message_id"],
        ondelete="CASCADE",
        name="fk_reactions_message",
    ),
)

# Indexes
Index("idx_reactions_message", reactions.c.chat_id, reactions.c.message_id)
Index("idx_reactions_from_user", reactions.c.from_user_id)
Index("idx_reactions_limit", reactions.c.chat_id, reactions.c.message_id, reactions.c.from_user_id)
