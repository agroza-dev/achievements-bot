"""Add users and groups tables

Revision ID: 001
Revises:
Create Date: 2025-12-24 11:15:00.00000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tg_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("username", sa.String(64)),
        sa.Column("first_name", sa.String(255)),
        sa.Column("last_name", sa.String(255)),
        sa.Column("is_bot", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "chats",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tg_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("settings", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "chat_users",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger, sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("chat_id", "user_id", name="uq_chat_user"),
    )


def downgrade():
    op.drop_table("chat_users")
    op.drop_table("chats")
    op.drop_table("users")
