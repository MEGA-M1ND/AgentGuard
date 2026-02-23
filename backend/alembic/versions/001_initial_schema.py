"""initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Detect database type
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    # Choose appropriate JSON type
    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())

    # Choose appropriate UUID type
    uuid_type = sa.String(36) if is_sqlite else postgresql.UUID(as_uuid=True)

    # Choose appropriate timestamp default
    timestamp_default = sa.text("(datetime('now'))") if is_sqlite else sa.text('now()')

    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('owner_team', sa.String(length=255), nullable=False),
        sa.Column('environment', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1' if is_sqlite else 'true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=timestamp_default),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=timestamp_default),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id')
    )
    op.create_index('ix_agents_agent_id', 'agents', ['agent_id'])
    op.create_index('ix_agents_environment', 'agents', ['environment'])
    op.create_index('ix_agents_is_active', 'agents', ['is_active'])

    # Create agent_keys table
    op.create_table(
        'agent_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(length=50), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('key_prefix', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1' if is_sqlite else 'true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=timestamp_default),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.agent_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    op.create_index('ix_agent_keys_agent_id', 'agent_keys', ['agent_id'])
    op.create_index('ix_agent_keys_key_prefix', 'agent_keys', ['key_prefix'])

    # Create policies table
    op.create_table(
        'policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(length=50), nullable=False),
        sa.Column('allow_rules', json_type, nullable=False, server_default='[]'),
        sa.Column('deny_rules', json_type, nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=timestamp_default),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=timestamp_default),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.agent_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id')
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('log_id', uuid_type, nullable=False),
        sa.Column('agent_id', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=timestamp_default),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('resource', sa.Text(), nullable=True),
        sa.Column('context', json_type, nullable=True),
        sa.Column('allowed', sa.Boolean(), nullable=False),
        sa.Column('result', sa.String(length=50), nullable=False),
        sa.Column('metadata', json_type, nullable=True),
        sa.Column('request_id', uuid_type, nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.agent_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('log_id')
    )
    op.create_index('ix_audit_logs_log_id', 'audit_logs', ['log_id'])
    op.create_index('ix_audit_logs_agent_id', 'audit_logs', ['agent_id'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_allowed', 'audit_logs', ['allowed'])
    # Composite index for common query patterns
    op.create_index('ix_audit_logs_agent_timestamp', 'audit_logs', ['agent_id', 'timestamp'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('policies')
    op.drop_table('agent_keys')
    op.drop_table('agents')
