"""Add agent_token to nodes table for Node Agent authentication.

Revision ID: 0003
Revises: 0002
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем поле agent_token в таблицу nodes
    # NULL = токен не настроен (агент не может подключиться)
    # Значение = секретный токен для аутентификации агента в Collector API
    op.add_column(
        'nodes',
        sa.Column('agent_token', sa.String(255), nullable=True, comment='Токен для аутентификации Node Agent')
    )
    
    # Индекс для быстрого поиска по токену
    op.create_index('idx_nodes_agent_token', 'nodes', ['agent_token'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_nodes_agent_token', table_name='nodes')
    op.drop_column('nodes', 'agent_token')
