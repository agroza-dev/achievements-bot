from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, MetaData, Table, func

metadata = MetaData()

chat_users = Table(
    "chat_users",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("chat_id", BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("is_admin", Boolean, nullable=False, server_default="false"),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("joined_at", DateTime(timezone=True), server_default=func.now()),
)
