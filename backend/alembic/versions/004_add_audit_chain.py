"""add previous_hash column to audit_logs for cryptographic chain

Revision ID: 004
Revises: 003
Create Date: 2026-02-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'audit_logs',
        sa.Column('previous_hash', sa.String(length=64), nullable=False, server_default='')
    )


def downgrade() -> None:
    op.drop_column('audit_logs', 'previous_hash')
