import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    # -----------------------
    # Таблица настроек пользователей
    # -----------------------
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.BigInteger, primary_key=True),

        # Notifications настройки
        sa.Column("notifications_enabled", sa.Boolean, nullable=False, server_default="true"),

        # Мета-поля
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_by_user_id", sa.BigInteger, nullable=True),

        # Foreign keys
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    # Индекс для быстрых запросов по updated_at
    op.create_index("idx_user_settings_updated_at", "user_settings", ["updated_at"])

    # -----------------------
    # Таблица истории изменений настроек
    # -----------------------
    op.create_table(
        "user_settings_history",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column("setting_name", sa.String(64), nullable=False),
        sa.Column("old_value", postgresql.JSONB, nullable=True),
        sa.Column("new_value", postgresql.JSONB, nullable=True),
        sa.Column("changed_by_user_id", sa.BigInteger, nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

        # Foreign keys
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    # Индексы для истории
    op.create_index("idx_user_settings_history_user_id", "user_settings_history", ["user_id"])
    op.create_index("idx_user_settings_history_changed_at", "user_settings_history", ["changed_at"])
    op.create_index("idx_user_settings_history_setting", "user_settings_history", ["setting_name"])

    # -----------------------
    # Создаём триггер для обновления updated_at
    # -----------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    op.execute("""
        CREATE TRIGGER update_user_settings_updated_at
            BEFORE UPDATE ON user_settings
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade():
    # Удаляем триггер и функцию
    op.execute("DROP TRIGGER IF EXISTS update_user_settings_updated_at ON user_settings")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Удаляем индексы
    op.drop_index("idx_user_settings_history_setting", table_name="user_settings_history")
    op.drop_index("idx_user_settings_history_changed_at", table_name="user_settings_history")
    op.drop_index("idx_user_settings_history_user_id", table_name="user_settings_history")
    op.drop_index("idx_user_settings_updated_at", table_name="user_settings")

    # Удаляем таблицы
    op.drop_table("user_settings_history")
    op.drop_table("user_settings")
