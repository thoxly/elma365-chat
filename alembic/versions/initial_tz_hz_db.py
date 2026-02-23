"""Initial migration for tz-hz database: create docs, doc_chunks, runs tables

Revision ID: initial_tz_hz_db
Revises: 
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'initial_tz_hz_db'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm;')
    
    # Create docs table
    op.create_table(
        'docs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doc_id', sa.String(), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('normalized_path', sa.Text(), nullable=True),
        sa.Column('outgoing_links', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('section', sa.Text(), nullable=True),
        sa.Column('content', postgresql.JSONB(), nullable=True),
        sa.Column('content_plain', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('last_crawled', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add embedding column as vector type
    op.execute("""
        ALTER TABLE docs 
        ADD COLUMN embedding vector(1536);
    """)
    
    # Create indexes on docs
    op.create_index(op.f('ix_docs_doc_id'), 'docs', ['doc_id'], unique=True)
    op.create_index(op.f('ix_docs_id'), 'docs', ['id'], unique=False)
    op.create_index(op.f('ix_docs_url'), 'docs', ['url'], unique=True)
    op.create_index('ix_docs_normalized_path', 'docs', ['normalized_path'], unique=True)
    op.create_index('ix_docs_outgoing_links_gin', 'docs', ['outgoing_links'], 
                    postgresql_using='gin', unique=False)
    op.execute("""
        CREATE INDEX docs_content_plain_trgm_idx
        ON docs USING gin (content_plain gin_trgm_ops);
    """)
    op.execute("""
        CREATE INDEX docs_embedding_idx
        ON docs USING ivfflat (embedding vector_cosine_ops);
    """)
    
    # Create doc_chunks table
    op.create_table(
        'doc_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doc_id', sa.String(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['doc_id'], ['docs.doc_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add embedding column as vector type
    op.execute("""
        ALTER TABLE doc_chunks 
        ADD COLUMN embedding vector(1536);
    """)
    
    # Create indexes on doc_chunks
    op.create_index('doc_chunks_doc_id_idx', 'doc_chunks', ['doc_id'], unique=False)
    op.execute("""
        CREATE INDEX doc_chunks_embedding_idx
        ON doc_chunks USING ivfflat (embedding vector_cosine_ops);
    """)
    
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
    
    op.execute('DROP INDEX IF EXISTS doc_chunks_embedding_idx;')
    op.drop_index('doc_chunks_doc_id_idx', table_name='doc_chunks')
    op.drop_table('doc_chunks')
    
    op.execute('DROP INDEX IF EXISTS docs_embedding_idx;')
    op.execute('DROP INDEX IF EXISTS docs_content_plain_trgm_idx;')
    op.drop_index('ix_docs_outgoing_links_gin', table_name='docs')
    op.drop_index('ix_docs_normalized_path', table_name='docs')
    op.drop_index(op.f('ix_docs_url'), table_name='docs')
    op.drop_index(op.f('ix_docs_id'), table_name='docs')
    op.drop_index(op.f('ix_docs_doc_id'), table_name='docs')
    op.drop_table('docs')

