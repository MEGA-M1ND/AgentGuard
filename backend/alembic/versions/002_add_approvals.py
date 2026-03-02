"""add approval_requests table and require_approval_rules column

Revision ID: 002
Revises: 001
Create Date: 2025-02-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Detect database type
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    # Choose appropriate types
    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    timestamp_default = sa.text("(datetime('now'))") if is_sqlite else sa.text('now()')

    # 1. Add require_approval_rules column to policies table
    op.add_column(
        'policies',
        sa.Column('require_approval_rules', json_type, nullable=False, server_default='[]')
    )

    # 2. Create approval_requests table
    op.create_table(
        'approval_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('approval_id', sa.String(length=36), nullable=False),
        sa.Column('agent_id', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('resource', sa.Text(), nullable=True),
        sa.Column('context', json_type, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=timestamp_default),
        sa.Column('decision_at', sa.DateTime(), nullable=True),
        sa.Column('decision_by', sa.String(length=50), nullable=True),
        sa.Column('decision_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.agent_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('approval_id')
    )
    op.create_index('ix_approval_requests_approval_id', 'approval_requests', ['approval_id'])
    op.create_index('ix_approval_requests_agent_id', 'approval_requests', ['agent_id'])
    op.create_index('ix_approval_requests_status', 'approval_requests', ['status'])
    op.create_index('ix_approval_requests_created_at', 'approval_requests', ['created_at'])
    # Composite index for common query: "pending approvals for an agent, sorted by time"
    op.create_index('ix_approval_requests_agent_status_time', 'approval_requests', ['agent_id', 'status', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_approval_requests_agent_status_time', table_name='approval_requests')
    op.drop_index('ix_approval_requests_created_at', table_name='approval_requests')
    op.drop_index('ix_approval_requests_status', table_name='approval_requests')
    op.drop_index('ix_approval_requests_agent_id', table_name='approval_requests')
    op.drop_index('ix_approval_requests_approval_id', table_name='approval_requests')
    op.drop_table('approval_requests')
    op.drop_column('policies', 'require_approval_rules')
