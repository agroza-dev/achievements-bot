from sqlalchemy import BigInteger, Boolean, Column, DateTime, MetaData, String, Table, func
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

chats = Table(
    "chats",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tg_id", BigInteger, nullable=False, unique=True),
    Column("type", String(32), nullable=False),
    Column("title", String(255), nullable=True),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("settings", JSONB, nullable=False, server_default="('{}')::jsonb"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now()),
)
