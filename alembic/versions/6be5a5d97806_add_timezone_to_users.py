# ruff: noqa
"""add timezone to users

Revision ID: 6be5a5d97806
Revises: 671cabe9ec56
Create Date: 2026-02-24 17:05:14.668128

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6be5a5d97806'
down_revision: Union[str, Sequence[str], None] = '671cabe9ec56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column('timezone', sa.String(length=64), nullable=False, server_default='Europe/Moscow')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'timezone')
