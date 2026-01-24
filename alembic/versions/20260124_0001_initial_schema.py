"""Initial schema for Remnawave Admin Bot database.

Revision ID: 0001
Revises: 
Create Date: 2026-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('uuid', sa.UUID(), nullable=False),
        sa.Column('short_uuid', sa.String(16), nullable=True),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('subscription_uuid', sa.UUID(), nullable=True),
        sa.Column('telegram_id', sa.BigInteger(), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('expire_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('traffic_limit_bytes', sa.BigInteger(), nullable=True),
        sa.Column('used_traffic_bytes', sa.BigInteger(), nullable=True),
        sa.Column('hwid_device_limit', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('uuid')
    )
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_telegram_id', 'users', ['telegram_id'])
    op.create_index('idx_users_status', 'users', ['status'])
    op.create_index('idx_users_short_uuid', 'users', ['short_uuid'])
    op.create_index('idx_users_subscription_uuid', 'users', ['subscription_uuid'])

    # Nodes table
    op.create_table(
        'nodes',
        sa.Column('uuid', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('address', sa.String(255), nullable=True),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('is_disabled', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('is_connected', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('traffic_limit_bytes', sa.BigInteger(), nullable=True),
        sa.Column('traffic_used_bytes', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('uuid')
    )
    op.create_index('idx_nodes_name', 'nodes', ['name'])
    op.create_index('idx_nodes_is_connected', 'nodes', ['is_connected'])

    # Hosts table
    op.create_table(
        'hosts',
        sa.Column('uuid', sa.UUID(), nullable=False),
        sa.Column('remark', sa.String(255), nullable=True),
        sa.Column('address', sa.String(255), nullable=True),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('is_disabled', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('uuid')
    )
    op.create_index('idx_hosts_remark', 'hosts', ['remark'])

    # Config profiles table
    op.create_table(
        'config_profiles',
        sa.Column('uuid', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('uuid')
    )

    # Sync metadata table
    op.create_table(
        'sync_metadata',
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_status', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('records_synced', sa.Integer(), server_default='0', nullable=True),
        sa.PrimaryKeyConstraint('key')
    )

    # User connections table (for future device tracking)
    op.create_table(
        'user_connections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_uuid', sa.UUID(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),  # Using String instead of INET for compatibility
        sa.Column('node_uuid', sa.UUID(), nullable=True),
        sa.Column('connected_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('disconnected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('device_info', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_uuid'], ['users.uuid'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['node_uuid'], ['nodes.uuid'], ondelete='SET NULL')
    )
    op.create_index('idx_user_connections_user', 'user_connections', ['user_uuid', 'connected_at'])
    op.create_index('idx_user_connections_ip', 'user_connections', ['ip_address'])
    op.create_index('idx_user_connections_node', 'user_connections', ['node_uuid'])


def downgrade() -> None:
    op.drop_table('user_connections')
    op.drop_table('sync_metadata')
    op.drop_table('config_profiles')
    op.drop_table('hosts')
    op.drop_table('nodes')
    op.drop_table('users')
