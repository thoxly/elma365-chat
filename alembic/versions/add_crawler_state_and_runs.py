"""add crawler_state and runs tables

Revision ID: add_crawler_state_runs
Revises: c84e8b4299e9
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_crawler_state_runs'
down_revision: Union[str, None] = 'c84e8b4299e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create crawler_state table
    op.create_table(
        'crawler_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('last_run', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pages_total', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('pages_processed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('status', sa.String(), nullable=True, server_default='idle'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crawler_state_id'), 'crawler_state', ['id'], unique=False)
    
    # Create runs table
    op.create_table(
        'runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('user', sa.String(), nullable=True),
        sa.Column('input_text', sa.Text(), nullable=True),
        sa.Column('as_is', postgresql.JSONB(), nullable=True),
        sa.Column('architecture', postgresql.JSONB(), nullable=True),
        sa.Column('scope', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_runs_id'), 'runs', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_runs_id'), table_name='runs')
    op.drop_table('runs')
    
    op.drop_index(op.f('ix_crawler_state_id'), table_name='crawler_state')
    op.drop_table('crawler_state')

