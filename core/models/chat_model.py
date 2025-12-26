from sqlalchemy import BigInteger, Boolean, Column, MetaData, String, Table

metadata = MetaData()

chats = Table(
    "chats",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("title", String, nullable=True),
    Column("type", String, nullable=False),
    Column("enabled", Boolean, nullable=False, server_default="true"),
)
