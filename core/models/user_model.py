from sqlalchemy import BigInteger, Boolean, Column, DateTime, MetaData, String, Table, func

metadata = MetaData()

user = Table(
    "users",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tg_id", BigInteger, nullable=False, unique=True),
    Column("username", String(64), nullable=True),
    Column("first_name", String(255), nullable=True),
    Column("last_name", String(255), nullable=True),
    Column("is_bot", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now()),
)
