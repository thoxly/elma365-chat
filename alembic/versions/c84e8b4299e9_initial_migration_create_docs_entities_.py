"""Initial migration: create docs, entities, specifications tables

Revision ID: c84e8b4299e9
Revises: 
Create Date: 2025-11-25 12:11:36.704696

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c84e8b4299e9'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create docs table
    op.create_table(
        'docs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doc_id', sa.String(), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('section', sa.Text(), nullable=True),
        sa.Column('content', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('last_crawled', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_docs_doc_id'), 'docs', ['doc_id'], unique=True)
    op.create_index(op.f('ix_docs_id'), 'docs', ['id'], unique=False)
    op.create_index(op.f('ix_docs_url'), 'docs', ['url'], unique=True)
    
    # Create entities table
    op.create_table(
        'entities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doc_id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('data', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['doc_id'], ['docs.doc_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_entities_doc_id'), 'entities', ['doc_id'], unique=False)
    op.create_index(op.f('ix_entities_id'), 'entities', ['id'], unique=False)
    op.create_index(op.f('ix_entities_type'), 'entities', ['type'], unique=False)
    
    # Create specifications table
    op.create_table(
        'specifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_text', sa.Text(), nullable=True),
        sa.Column('analyst_json', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('architect_json', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('spec_markdown', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_specifications_id'), 'specifications', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_specifications_id'), table_name='specifications')
    op.drop_table('specifications')
    
    op.drop_index(op.f('ix_entities_type'), table_name='entities')
    op.drop_index(op.f('ix_entities_id'), table_name='entities')
    op.drop_index(op.f('ix_entities_doc_id'), table_name='entities')
    op.drop_table('entities')
    
    op.drop_index(op.f('ix_docs_url'), table_name='docs')
    op.drop_index(op.f('ix_docs_id'), table_name='docs')
    op.drop_index(op.f('ix_docs_doc_id'), table_name='docs')
    op.drop_table('docs')

