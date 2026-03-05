import sqlalchemy as sa

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    # -----------------------
    # Таблица для пакетов периодических зачислений
    # -----------------------
    op.create_table(
        "award_batches",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger, sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_key", sa.String(20), nullable=False),  # Формат: "2026-W09"
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),  # pending|processing|done
        sa.Column("cursor_user_id", sa.BigInteger, nullable=True),  # ID последнего обработанного пользователя
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("chat_id", "period_key", name="uq_award_batch_chat_period"),
    )

    # Индекс для быстрого поиска незавершённых batch
    op.create_index("idx_award_batches_status", "award_batches", ["status"])
    op.create_index("idx_award_batches_chat_period", "award_batches", ["chat_id", "period_key"])

    # -----------------------
    # Добавляем operation_key в rating_ledger для idempotency periodic_award
    # -----------------------
    # Добавляем колонку operation_key
    op.add_column("rating_ledger", sa.Column("operation_key", sa.String(64), nullable=True))

    # Заполняем operation_key для существующих записей:
    # - periodic_award записи получают period_key из meta (если есть)
    # - все остальные записи получают пустую строку
    # Это безопасно потому что UNIQUE constraint будет добавлен после заполнения
    op.execute("""
        UPDATE rating_ledger
        SET operation_key = COALESCE(meta->>'period_key', '')
        WHERE operation_key IS NULL
    """)

    # Делаем operation_key NOT NULL (теперь все записи имеют значение)
    op.alter_column("rating_ledger", "operation_key", existing_type=sa.String(64), nullable=False, server_default='')

    # Находим и удаляем дубликаты periodic_award перед созданием уникального индекса
    # Оставляем только самую новую запись для каждого (user_id, operation_key)
    op.execute("""
        DELETE FROM rating_ledger rl1
        USING rating_ledger rl2
        WHERE rl1.operation_type = 'award'
          AND rl1.operation_subtype = 'periodic_award'
          AND rl2.operation_type = 'award'
          AND rl2.operation_subtype = 'periodic_award'
          AND rl1.user_id = rl2.user_id
          AND rl1.operation_key = rl2.operation_key
          AND rl1.ctid < rl2.ctid
    """)

    # Добавляем partial UNIQUE индекс ТОЛЬКО для periodic_award
    # Это обеспечивает idempotency: один пользователь — одно зачисление за период В КАЖДОМ чате
    # Transfer/reaction/tax НЕ попадают под этот индекс и работают как прежде
    # Сначала удаляем индекс если существует (для идемпотентности миграции)
    op.execute("DROP INDEX IF EXISTS uq_rating_ledger_periodic_award")
    op.execute("""
        CREATE UNIQUE INDEX
        uq_rating_ledger_periodic_award
        ON rating_ledger (chat_id, user_id, operation_key)
        WHERE operation_type = 'award' AND operation_subtype = 'periodic_award'
    """)


def downgrade():
    # Удаляем partial unique constraint
    op.execute("ALTER TABLE rating_ledger DROP CONSTRAINT IF EXISTS uq_rating_ledger_periodic_award")

    # Делаем operation_key снова nullable
    op.alter_column("rating_ledger", "operation_key", existing_type=sa.String(64), nullable=True)

    # Удаляем колонку operation_key
    op.drop_column("rating_ledger", "operation_key")

    # Удаляем индексы
    op.drop_index("idx_award_batches_chat_period", table_name="award_batches")
    op.drop_index("idx_award_batches_status", table_name="award_batches")

    # Удаляем таблицу
    op.drop_table("award_batches")
