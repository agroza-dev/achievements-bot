"""003_add_foreign_keys_to_reactions

Revision ID: 671cabe9ec56
Revises: e521f296cb89
Create Date: 2026-02-24 14:54:13.446511

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '671cabe9ec56'
down_revision: Union[str, Sequence[str], None] = 'e521f296cb89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Сначала очистим "висячие" реакции, которые ссылаются на удалённые записи
    
    # Удаляем реакции, где chat_id не существует в chats
    op.execute("""
        DELETE FROM reactions r
        WHERE NOT EXISTS (
            SELECT 1 FROM chats c WHERE c.id = r.chat_id
        )
    """)
    
    # Удаляем реакции, где from_user_id не существует в users
    op.execute("""
        DELETE FROM reactions r
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE u.id = r.from_user_id
        )
    """)
    
    # Удаляем реакции, где to_user_id не существует в users
    op.execute("""
        DELETE FROM reactions r
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE u.id = r.to_user_id
        )
    """)
    
    # Удаляем реакции, где сообщение не существует в chat_messages
    op.execute("""
        DELETE FROM reactions r
        WHERE NOT EXISTS (
            SELECT 1 FROM chat_messages cm 
            WHERE cm.chat_id = r.chat_id AND cm.tg_message_id = r.message_id
        )
    """)
    
    # Добавляем внешние ключи с CASCADE
    
    # FK на chats (CASCADE при удалении чата)
    op.create_foreign_key(
        constraint_name='fk_reactions_chat',
        source_table='reactions',
        referent_table='chats',
        local_cols=['chat_id'],
        remote_cols=['id'],
        ondelete='CASCADE'
    )
    
    # FK на users для from_user_id (CASCADE при удалении пользователя)
    op.create_foreign_key(
        constraint_name='fk_reactions_from_user',
        source_table='reactions',
        referent_table='users',
        local_cols=['from_user_id'],
        remote_cols=['id'],
        ondelete='CASCADE'
    )
    
    # FK на users для to_user_id (CASCADE при удалении пользователя)
    op.create_foreign_key(
        constraint_name='fk_reactions_to_user',
        source_table='reactions',
        referent_table='users',
        local_cols=['to_user_id'],
        remote_cols=['id'],
        ondelete='CASCADE'
    )
    
    # FK на chat_messages с составным ключом (CASCADE при удалении сообщения)
    op.create_foreign_key(
        constraint_name='fk_reactions_message',
        source_table='reactions',
        referent_table='chat_messages',
        local_cols=['chat_id', 'message_id'],
        remote_cols=['chat_id', 'tg_message_id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем внешние ключи в обратном порядке
    op.drop_constraint('fk_reactions_message', 'reactions', type_='foreignkey')
    op.drop_constraint('fk_reactions_to_user', 'reactions', type_='foreignkey')
    op.drop_constraint('fk_reactions_from_user', 'reactions', type_='foreignkey')
    op.drop_constraint('fk_reactions_chat', 'reactions', type_='foreignkey')
