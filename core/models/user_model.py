from sqlalchemy import BigInteger, Boolean, Column, MetaData, String, Table

metadata = MetaData()

user = Table(
    "users",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("username", String, nullable=True),
    Column("first_name", String, nullable=True),
    Column("last_name", String, nullable=True),
    Column("is_bot", Boolean, nullable=False),
)
