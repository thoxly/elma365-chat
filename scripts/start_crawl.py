#!/usr/bin/env python3
"""
Скрипт для запуска краулинга и записи документов в базу данных.
"""
import asyncio
import sys
import logging
from pathlib import Path
from typing import Dict

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.crawler import Crawler
from app.crawler.storage import Storage
from app.database.database import get_session_factory
from app.config import settings

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def crawl_and_save(start_url: str = None, max_pages: int = None, platform_only: bool = False):
    """
    Запускает краулинг и сохраняет документы в базу данных.
    
    Args:
        start_url: Начальный URL для краулинга. Если None, используется /ru/help/platform/
        max_pages: Максимальное количество страниц для краулинга (None = без ограничений)
        platform_only: Если True, краулит только ссылки из /ru/help/platform/
    """
    logger.info("=" * 60)
    logger.info("Запуск краулинга и записи документов в базу данных")
    logger.info("=" * 60)
    
    # Получаем фабрику сессий
    session_factory = get_session_factory()
    
    # Создаем сессию базы данных
    async with session_factory() as session:
        try:
            # Создаем краулер с сессией БД для отслеживания состояния
            crawler = Crawler(db_session=session, max_pages=max_pages, platform_only=platform_only)
            storage = Storage()
            
            saved_count = 0
            failed_count = 0
            
            async def save_doc_immediately(doc_data: Dict):
                """Callback to save each document as soon as it's crawled."""
                nonlocal saved_count, failed_count
                try:
                    result = await storage.save(session, doc_data)
                    await session.commit()
                    
                    if result.get('db_saved'):
                        saved_count += 1
                        logger.info(f"✓ Сохранен документ: {doc_data.get('doc_id')} (всего: {saved_count})")
                    else:
                        failed_count += 1
                        logger.warning(f"✗ Не удалось сохранить документ: {doc_data.get('doc_id')}")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Ошибка при сохранении документа {doc_data.get('doc_id')}: {e}")
                    await session.rollback()
            
            # Запускаем краулинг
            if start_url is None:
                start_url = f'{settings.CRAWL_BASE_URL}/ru/help/platform/'
            logger.info(f"Начало краулинга с URL: {start_url}")
            if max_pages:
                logger.info(f"Ограничение: максимум {max_pages} страниц")
            if platform_only:
                logger.info("Режим: только /ru/help/platform/ ссылки")
            logger.info("Документы будут сохраняться в базу данных по мере получения...")
            
            async with crawler:
                # Pass callback to save documents immediately (not in memory!)
                docs = await crawler.crawl_recursive(start_url, on_doc_crawled=save_doc_immediately)
            
            logger.info(f"Краулинг завершен. Получено документов: {len(docs)}")
            logger.info("=" * 60)
            logger.info(f"Итоги:")
            logger.info(f"  Всего документов: {len(docs)}")
            logger.info(f"  Успешно сохранено: {saved_count}")
            logger.info(f"  Ошибок: {failed_count}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
            await session.rollback()
            raise


async def main():
    """Главная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Запуск краулинга и записи документов в базу данных')
    parser.add_argument(
        '--url',
        type=str,
        default=None,
        help='Начальный URL для краулинга (по умолчанию: /ru/help/platform/)'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=None,
        help='Максимальное количество страниц для краулинга (по умолчанию: без ограничений)'
    )
    parser.add_argument(
        '--platform-only',
        action='store_true',
        help='Краулить только ссылки из /ru/help/platform/'
    )
    
    args = parser.parse_args()
    
    try:
        await crawl_and_save(args.url, max_pages=args.max_pages, platform_only=args.platform_only)
    except KeyboardInterrupt:
        logger.info("\nКраулинг прерван пользователем")
    except Exception as e:
        logger.error(f"Ошибка выполнения: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

