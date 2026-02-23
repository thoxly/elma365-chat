"""Remove runs table

Revision ID: remove_runs_table
Revises: initial_tz_hz_db
Create Date: 2025-02-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_runs_table'
down_revision: Union[str, None] = 'initial_tz_hz_db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop runs table (no longer needed after removing pipeline)
    op.drop_index(op.f('ix_runs_id'), table_name='runs')
    op.drop_table('runs')


def downgrade() -> None:
    # Recreate runs table if needed
    op.create_table(
        'runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('user', sa.String(), nullable=True),
        sa.Column('input_text', sa.Text(), nullable=True),
        sa.Column('as_is', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('architecture', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('scope', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_runs_id'), 'runs', ['id'], unique=False)
