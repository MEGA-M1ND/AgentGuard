"""add admin_users and team_policies tables for RBAC

Revision ID: 005
Revises: 004
Create Date: 2026-02-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    timestamp_default = sa.text("(datetime('now'))") if is_sqlite else sa.text('now()')

    # ------------------------------------------------------------------
    # admin_users
    # ------------------------------------------------------------------
    op.create_table(
        'admin_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('key_prefix', sa.String(length=20), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('team', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=timestamp_default),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('admin_id'),
        sa.UniqueConstraint('key_hash'),
    )
    op.create_index('ix_admin_users_admin_id', 'admin_users', ['admin_id'], unique=True)
    op.create_index('ix_admin_users_key_prefix', 'admin_users', ['key_prefix'])

    # ------------------------------------------------------------------
    # team_policies
    # ------------------------------------------------------------------
    op.create_table(
        'team_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team', sa.String(length=255), nullable=False),
        sa.Column('allow_rules', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('deny_rules', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('require_approval_rules', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=timestamp_default),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=timestamp_default),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team'),
    )
    op.create_index('ix_team_policies_team', 'team_policies', ['team'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_team_policies_team', table_name='team_policies')
    op.drop_table('team_policies')

    op.drop_index('ix_admin_users_key_prefix', table_name='admin_users')
    op.drop_index('ix_admin_users_admin_id', table_name='admin_users')
    op.drop_table('admin_users')
