import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    # -----------------------
    # Таблица настроек чатов
    # -----------------------
    op.create_table(
        "chat_settings",
        sa.Column("chat_id", sa.BigInteger, primary_key=True),

        # Periodic award настройки
        sa.Column("periodic_award_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("periodic_award_amount", sa.Integer, nullable=True),  # NULL = использовать дефолт из конфига

        # Tax настройки
        sa.Column("tax_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False, server_default="0.00"),  # 0.00 - 99.99 (проценты)

        # Мета-поля
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_by_user_id", sa.BigInteger, nullable=True),

        # Foreign keys
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    # Индекс для быстрых запросов по updated_at
    op.create_index("idx_chat_settings_updated_at", "chat_settings", ["updated_at"])

    # -----------------------
    # Таблица истории изменений настроек
    # -----------------------
    op.create_table(
        "chat_settings_history",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger, nullable=False),
        sa.Column("setting_name", sa.String(64), nullable=False),  # Например: "periodic_award.amount"
        sa.Column("old_value", postgresql.JSONB, nullable=True),
        sa.Column("new_value", postgresql.JSONB, nullable=True),
        sa.Column("changed_by_user_id", sa.BigInteger, nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

        # Foreign keys
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    # Индексы для истории
    op.create_index("idx_chat_settings_history_chat_id", "chat_settings_history", ["chat_id"])
    op.create_index("idx_chat_settings_history_changed_at", "chat_settings_history", ["changed_at"])
    op.create_index("idx_chat_settings_history_setting", "chat_settings_history", ["setting_name"])

    # -----------------------
    # Миграция данных из старого JSONB в новую таблицу
    # -----------------------
    op.execute("""
        INSERT INTO chat_settings (
            chat_id,
            periodic_award_enabled,
            periodic_award_amount,
            tax_enabled,
            tax_rate,
            updated_by_user_id
        )
        SELECT
            c.id as chat_id,
            -- Periodic award
            COALESCE(
                (c.settings->'periodic_award'->>'enabled')::boolean,
                true
            ) as periodic_award_enabled,
            -- Amount: NULL если не задан (будет использоваться дефолт из конфига)
            NULLIF((c.settings->'periodic_award'->>'amount')::integer, 0) as periodic_award_amount,
            -- Tax
            COALESCE(
                (c.settings->'tax'->>'enabled')::boolean,
                false
            ) as tax_enabled,
            COALESCE(
                (c.settings->'tax'->>'rate')::numeric,
                0.0000
            ) as tax_rate,
            NULL as updated_by_user_id
        FROM chats c
        WHERE c.is_active = true
    """)

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
        CREATE TRIGGER update_chat_settings_updated_at
            BEFORE UPDATE ON chat_settings
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # -----------------------
    # Удаляем старое поле settings из chats
    # -----------------------
    op.drop_column("chats", "settings")


def downgrade():
    # Возвращаем поле settings
    op.add_column(
        "chats",
        sa.Column(
            "settings",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb")
        ),
    )

    # Возвращаем данные из новой таблицы в старое JSONB поле
    op.execute("""
        UPDATE chats c
        SET settings = jsonb_build_object(
            'periodic_award', jsonb_build_object(
                'enabled', cs.periodic_award_enabled,
                'amount', cs.periodic_award_amount
            ),
            'tax', jsonb_build_object(
                'enabled', cs.tax_enabled,
                'rate', cs.tax_rate
            )
        )
        FROM chat_settings cs
        WHERE c.id = cs.chat_id
    """)

    # Удаляем триггер и функцию
    op.execute("DROP TRIGGER IF EXISTS update_chat_settings_updated_at ON chat_settings")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Возвращаем данные из новой таблицы в старое JSONB поле (если нужно)
    op.execute("""
        UPDATE chats c
        SET settings = jsonb_build_object(
            'periodic_award', jsonb_build_object(
                'enabled', cs.periodic_award_enabled,
                'amount', cs.periodic_award_amount
            ),
            'tax', jsonb_build_object(
                'enabled', cs.tax_enabled,
                'rate', cs.tax_rate
            )
        )
        FROM chat_settings cs
        WHERE c.id = cs.chat_id
    """)

    # Удаляем индексы
    op.drop_index("idx_chat_settings_history_setting", table_name="chat_settings_history")
    op.drop_index("idx_chat_settings_history_changed_at", table_name="chat_settings_history")
    op.drop_index("idx_chat_settings_history_chat_id", table_name="chat_settings_history")
    op.drop_index("idx_chat_settings_updated_at", table_name="chat_settings")

    # Удаляем таблицы
    op.drop_table("chat_settings_history")
    op.drop_table("chat_settings")
