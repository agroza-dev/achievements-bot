from sqlalchemy import BigInteger, Column, DateTime, Index, String, Table, func

from core.models.metadata import metadata

reactions = Table(
    "reactions",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("chat_id", BigInteger, nullable=False),
    Column("message_id", BigInteger, nullable=False),
    Column("from_user_id", BigInteger, nullable=False),
    Column("to_user_id", BigInteger, nullable=False),
    Column("reaction", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

# Indexes
Index("idx_reactions_message", reactions.c.chat_id, reactions.c.message_id)
Index("idx_reactions_from_user", reactions.c.from_user_id)
Index("idx_reactions_limit", reactions.c.chat_id, reactions.c.message_id, reactions.c.from_user_id)
