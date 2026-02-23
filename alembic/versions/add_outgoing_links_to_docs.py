"""add outgoing_links to docs table

Revision ID: add_outgoing_links
Revises: add_normalized_path
Create Date: 2025-11-30 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_outgoing_links'
down_revision: Union[str, None] = 'add_normalized_path'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add outgoing_links column to docs table
    op.add_column('docs', sa.Column('outgoing_links', postgresql.ARRAY(sa.Text()), nullable=True))
    
    # Create GIN index for efficient array queries
    op.create_index('ix_docs_outgoing_links_gin', 'docs', ['outgoing_links'], 
                    postgresql_using='gin', unique=False)
    
    # Fill outgoing_links for existing documents with normalized blocks
    # This requires executing Python code
    connection = op.get_bind()
    
    # Import extract_outgoing_links function
    import sys
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from app.utils import extract_outgoing_links
    
    # Update all existing records that have normalized blocks
    result = connection.execute(sa.text("""
        SELECT id, content 
        FROM docs 
        WHERE content->'blocks' IS NOT NULL 
          AND (outgoing_links IS NULL OR array_length(outgoing_links, 1) IS NULL)
    """))
    rows = result.fetchall()
    
    updated_count = 0
    for row in rows:
        doc_id, content = row[0], row[1]
        try:
            if content and 'blocks' in content:
                blocks = content.get('blocks', [])
                if blocks:
                    outgoing = extract_outgoing_links(blocks)
                    if outgoing:
                        # Convert to PostgreSQL array format
                        connection.execute(
                            sa.text("UPDATE docs SET outgoing_links = :links WHERE id = :id"),
                            {"links": outgoing, "id": doc_id}
                        )
                        updated_count += 1
        except Exception as e:
            print(f"Error extracting links for doc_id {doc_id}: {e}")
    
    # Commit the updates
    connection.commit()
    
    print(f"Updated outgoing_links for {updated_count} documents")


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_docs_outgoing_links_gin', table_name='docs')
    
    # Drop column
    op.drop_column('docs', 'outgoing_links')

