"""Add chat_sessions table for listing and titling chats

Revision ID: add_chat_sessions
Revises: add_chat_tables
Create Date: 2025-02-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_chat_sessions'
down_revision: Union[str, None] = 'add_chat_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False, server_default='Новый чат'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chat_sessions_id'), 'chat_sessions', ['id'], unique=False)
    op.create_index('ix_chat_sessions_session_id', 'chat_sessions', ['session_id'], unique=True)
    op.create_index('ix_chat_sessions_user_id', 'chat_sessions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_chat_sessions_user_id', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_session_id', table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_id'), table_name='chat_sessions')
    op.drop_table('chat_sessions')
