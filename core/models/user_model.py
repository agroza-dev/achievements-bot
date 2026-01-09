from sqlalchemy import BigInteger, Boolean, Column, DateTime, String, Table, func

from core.models.metadata import metadata

users = Table(
    "users",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("tg_id", BigInteger, nullable=False, unique=True),
    Column("username", String(64)),
    Column("first_name", String(255)),
    Column("last_name", String(255)),
    Column("is_bot", Boolean, nullable=False, server_default="false"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now()),
)
