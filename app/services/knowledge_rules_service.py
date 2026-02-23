"""Service for managing knowledge rules in the database."""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import KnowledgeRule
import yaml
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class KnowledgeRulesService:
    """Service for working with ELMA365 knowledge rules."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def get_rule(self, rule_type: str) -> Optional[Dict[str, Any]]:
        """Get a rule by type."""
        result = await self.db_session.execute(
            select(KnowledgeRule).where(KnowledgeRule.rule_type == rule_type)
        )
        rule = result.scalar_one_or_none()
        if rule:
            return {
                "rule_type": rule.rule_type,
                "content": rule.content,
                "version": rule.version,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
                "updated_by": rule.updated_by
            }
        return None
    
    async def update_rule(self, rule_type: str, content: Dict[str, Any], updated_by: str) -> KnowledgeRule:
        """Update or create a rule."""
        result = await self.db_session.execute(
            select(KnowledgeRule).where(KnowledgeRule.rule_type == rule_type)
        )
        rule = result.scalar_one_or_none()
        
        if rule:
            rule.content = content
            rule.version = rule.version + 1
            rule.updated_by = updated_by
        else:
            rule = KnowledgeRule(
                rule_type=rule_type,
                content=content,
                version=1,
                updated_by=updated_by
            )
            self.db_session.add(rule)
        
        await self.db_session.commit()
        await self.db_session.refresh(rule)
        return rule
    
    async def get_all_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get all rules."""
        result = await self.db_session.execute(select(KnowledgeRule))
        rules = result.scalars().all()
        
        return {
            rule.rule_type: {
                "content": rule.content,
                "version": rule.version,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
                "updated_by": rule.updated_by
            }
            for rule in rules
        }
    
    async def migrate_from_files(self, rules_dir: Path) -> Dict[str, int]:
        """Migrate rules from files to database (one-time operation)."""
        migrated = {}
        
        # Map file names to rule types
        file_mapping = {
            "ARCHITECTURE_RULES_ELMA365.md": "architecture_rules",
            "PROCESS_RULES_ELMA365.md": "process_rules",
            "UI_RULES_ELMA365.md": "ui_rules",
            "elma365_arch_dictionary.yml": "dictionary",
            "ENGINEERING_PATTERNS_ELMA365.yml": "patterns"
        }
        
        for filename, rule_type in file_mapping.items():
            file_path = rules_dir / filename
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue
            
            try:
                if filename.endswith('.yml') or filename.endswith('.yaml'):
                    # YAML file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content_dict = yaml.safe_load(f)
                    content = {"yaml": content_dict}
                else:
                    # Markdown file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    content = {"text": text}
                
                await self.update_rule(rule_type, content, "system")
                migrated[rule_type] = 1
                logger.info(f"Migrated {rule_type} from {filename}")
            except Exception as e:
                logger.error(f"Error migrating {filename}: {e}")
                migrated[rule_type] = 0
        
        return migrated
