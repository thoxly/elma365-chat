"""add embeddings and chunks

Revision ID: add_embeddings_and_chunks
Revises: add_outgoing_links
Create Date: 2025-12-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_embeddings_and_chunks'
down_revision: Union[str, None] = 'add_outgoing_links'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm;')
    
    # Add content_plain column to docs table
    op.add_column('docs', sa.Column('content_plain', sa.Text(), nullable=True))
    
    # Add embedding column to docs table (vector(1536) for text-embedding-3-small)
    op.execute("""
        ALTER TABLE docs 
        ADD COLUMN embedding vector(1536);
    """)
    
    # Create GIN index on content_plain with pg_trgm for full-text search
    op.execute("""
        CREATE INDEX docs_content_plain_trgm_idx
        ON docs USING gin (content_plain gin_trgm_ops);
    """)
    
    # Create IVFFlat index on embedding for vector search
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
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['doc_id'], ['docs.doc_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add embedding column to doc_chunks table
    op.execute("""
        ALTER TABLE doc_chunks 
        ADD COLUMN embedding vector(1536);
    """)
    
    # Create indexes on doc_chunks
    op.create_index('doc_chunks_doc_id_idx', 'doc_chunks', ['doc_id'], unique=False)
    
    # Create IVFFlat index on doc_chunks.embedding
    op.execute("""
        CREATE INDEX doc_chunks_embedding_idx
        ON doc_chunks USING ivfflat (embedding vector_cosine_ops);
    """)


def downgrade() -> None:
    # Drop indexes
    op.execute('DROP INDEX IF EXISTS doc_chunks_embedding_idx;')
    op.drop_index('doc_chunks_doc_id_idx', table_name='doc_chunks')
    op.execute('DROP INDEX IF EXISTS docs_embedding_idx;')
    op.execute('DROP INDEX IF EXISTS docs_content_plain_trgm_idx;')
    
    # Drop doc_chunks table
    op.drop_table('doc_chunks')
    
    # Drop columns from docs table
    op.drop_column('docs', 'embedding')
    op.drop_column('docs', 'content_plain')
    
    # Note: We don't drop extensions as they might be used by other tables

