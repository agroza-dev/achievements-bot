"""add bot_persistence table

Revision ID: e521f296cb89
Revises: 4e00fdd8041a
Create Date: 2026-02-24 09:24:50.423641

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e521f296cb89'
down_revision: str | Sequence[str] | None = '4e00fdd8041a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'bot_persistence',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=True),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('bot_data', sa.JSON(), nullable=True),
        sa.Column('chat_data', sa.JSON(), nullable=True),
        sa.Column('user_data', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('chat_id', 'user_id', name='uq_chat_id_user_id'),
    )
    op.create_index('idx_bot_persistence_chat_id', 'bot_persistence', ['chat_id'])
    op.create_index('idx_bot_persistence_user_id', 'bot_persistence', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_bot_persistence_user_id', table_name='bot_persistence')
    op.drop_index('idx_bot_persistence_chat_id', table_name='bot_persistence')
    op.drop_table('bot_persistence')
