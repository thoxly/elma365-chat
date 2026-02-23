"""add normalized_path to docs table

Revision ID: add_normalized_path
Revises: add_crawler_state_runs
Create Date: 2025-11-30 13:21:50.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_normalized_path'
down_revision: Union[str, None] = 'add_crawler_state_runs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add normalized_path column to docs table (nullable first)
    op.add_column('docs', sa.Column('normalized_path', sa.Text(), nullable=True))
    
    # Fill normalized_path for existing records using Python function
    # This requires executing Python code, so we use op.get_bind()
    connection = op.get_bind()
    
    # Import normalize_path function
    import sys
    import os
    # Add project root to path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from app.utils import normalize_path
    
    # Update all existing records
    result = connection.execute(sa.text("SELECT id, url FROM docs WHERE normalized_path IS NULL"))
    rows = result.fetchall()
    
    updated_count = 0
    for row in rows:
        doc_id, url = row[0], row[1]
        try:
            normalized = normalize_path(url)
            if normalized:  # Only update if we got a valid normalized path
                connection.execute(
                    sa.text("UPDATE docs SET normalized_path = :normalized WHERE id = :id"),
                    {"normalized": normalized, "id": doc_id}
                )
                updated_count += 1
        except Exception as e:
            # Log error but continue
            print(f"Error normalizing path for doc_id {doc_id}, url {url}: {e}")
    
    # Commit the updates
    connection.commit()
    
    print(f"Updated normalized_path for {updated_count} documents")
    
    # Create unique index on normalized_path (after filling data)
    op.create_index('ix_docs_normalized_path', 'docs', ['normalized_path'], unique=True)
    
    # Note: We keep the column nullable=True to allow for edge cases
    # In practice, all valid help URLs should have normalized_path


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_docs_normalized_path', table_name='docs')
    
    # Drop column
    op.drop_column('docs', 'normalized_path')

