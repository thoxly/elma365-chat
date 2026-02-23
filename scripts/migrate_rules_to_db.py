#!/usr/bin/env python3
"""
Script to migrate knowledge rules from files to database.
One-time operation.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database.database import get_session_factory
from app.services.knowledge_rules_service import KnowledgeRulesService


async def main():
    """Migrate rules from files to database."""
    rules_dir = project_root / "data" / "knowledge_rules"
    
    if not rules_dir.exists():
        print(f"❌ Rules directory not found: {rules_dir}")
        sys.exit(1)
    
    print(f"📁 Migrating rules from: {rules_dir}")
    print()
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        service = KnowledgeRulesService(session)
        migrated = await service.migrate_from_files(rules_dir)
        
        print()
        print("=" * 50)
        print("Migration results:")
        print("=" * 50)
        
        total = len(migrated)
        success = sum(1 for v in migrated.values() if v == 1)
        
        for rule_type, status in migrated.items():
            status_icon = "✅" if status == 1 else "❌"
            print(f"{status_icon} {rule_type}")
        
        print()
        print(f"Total: {success}/{total} rules migrated successfully")
        
        if success == total:
            print("✅ Migration completed successfully!")
        else:
            print("⚠️  Some rules failed to migrate. Check logs above.")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
