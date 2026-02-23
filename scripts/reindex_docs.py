#!/usr/bin/env python3
"""
Скрипт для пересчета plaintext, chunks и embeddings для существующих документов.
Обрабатывает документы пакетами для избежания rate limiting.
"""
import asyncio
import sys
import logging
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, text
from app.database.database import get_session_factory
from app.database.models import Doc
from app.crawler.storage import Storage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def reindex_docs(batch_size: int = 30):
    """
    Пересчитать plaintext, chunks и embeddings для всех документов с нормализованным контентом.
    
    Args:
        batch_size: Количество документов для обработки в одном пакете (для rate limiting)
    """
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        try:
            # Get all documents with normalized content
            result = await session.execute(
                select(Doc).where(
                    Doc.content.isnot(None),
                    text("content->'blocks' IS NOT NULL")
                )
            )
            all_docs = result.scalars().all()
            total_docs = len(all_docs)
            
            logger.info(f"Found {total_docs} documents with normalized content")
            
            if total_docs == 0:
                logger.warning("No documents with normalized content found")
                return
            
            storage = Storage()
            
            processed = 0
            errors = 0
            skipped = 0
            
            # Process in batches
            for i in range(0, total_docs, batch_size):
                batch = all_docs[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_docs + batch_size - 1) // batch_size
                
                logger.info(
                    f"Processing batch {batch_num}/{total_batches} "
                    f"({len(batch)} documents, {processed}/{total_docs} total processed)"
                )
                
                for doc in batch:
                    try:
                        # Check if content has blocks
                        content = doc.content or {}
                        if 'blocks' not in content:
                            skipped += 1
                            logger.debug(f"Skipping {doc.doc_id}: no blocks in content")
                            continue
                        
                        logger.info(f"Processing embeddings for {doc.doc_id}...")
                        
                        # Process embeddings (plaintext, chunks, embeddings)
                        await storage.process_embeddings_for_doc(session, doc)
                        
                        processed += 1
                        
                        # Log progress every 10 documents
                        if processed % 10 == 0:
                            logger.info(
                                f"Progress: {processed}/{total_docs} processed, "
                                f"{skipped} skipped, {errors} errors"
                            )
                    
                    except Exception as e:
                        errors += 1
                        logger.error(
                            f"Error processing embeddings for {doc.doc_id}: {e}",
                            exc_info=True
                        )
                        await session.rollback()
                        # Continue with next document
                        continue
                
                # Small delay between batches to avoid rate limiting
                if i + batch_size < total_docs:
                    logger.debug(f"Waiting 2 seconds before next batch...")
                    await asyncio.sleep(2)
            
            logger.info("=" * 60)
            logger.info("Reindexing completed!")
            logger.info(f"  Processed: {processed}")
            logger.info(f"  Skipped: {skipped}")
            logger.info(f"  Errors: {errors}")
            logger.info("=" * 60)
        
        except Exception as e:
            logger.error(f"Error in reindex_docs: {e}", exc_info=True)
            await session.rollback()
            raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Reindex all documents: calculate plaintext, chunks, and embeddings"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=30,
        help="Number of documents to process in one batch (default: 30)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(reindex_docs(batch_size=args.batch_size))

