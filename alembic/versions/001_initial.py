import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # -----------------------
    # Users table
    # -----------------------
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

    # -----------------------
    # Chats table
    # -----------------------
    op.create_table(
        "chats",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tg_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "settings",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # -----------------------
    # ChatUsers table
    # -----------------------
    op.create_table(
        "chat_users",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger, sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("rating", sa.Integer, nullable=True, server_default="0"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("chat_id", "user_id", name="uq_chat_user"),
    )

    # -----------------------
    # ChatMessages table
    # -----------------------
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger, sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tg_message_id", sa.BigInteger, nullable=False),
        sa.Column("author_user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("message_type", sa.String(32), nullable=False),
        sa.Column(
            "message_meta",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stored_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("chat_id", "tg_message_id", name="uq_chat_message"),
    )

    # -----------------------
    # Reactions table
    # -----------------------
    op.create_table(
        "reactions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger, nullable=False),
        sa.Column("message_id", sa.BigInteger, nullable=False),
        sa.Column("from_user_id", sa.BigInteger, nullable=False),
        sa.Column("to_user_id", sa.BigInteger, nullable=False),
        sa.Column("reaction", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Indexes for reactions
    op.create_index("idx_reactions_message", "reactions", ["chat_id", "message_id"])
    op.create_index("idx_reactions_from_user", "reactions", ["from_user_id"])
    op.create_index("idx_reactions_limit", "reactions", ["chat_id", "message_id", "from_user_id"])


def downgrade():
    # Drop in reverse order to respect FK dependencies
    op.drop_index("idx_reactions_limit", table_name="reactions")
    op.drop_index("idx_reactions_from_user", table_name="reactions")
    op.drop_index("idx_reactions_message", table_name="reactions")
    op.drop_table("reactions")
    op.drop_table("chat_messages")
    op.drop_table("chat_users")
    op.drop_table("chats")
    op.drop_table("users")