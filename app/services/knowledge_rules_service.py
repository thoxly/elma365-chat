"""Service for managing knowledge rules (Supabase API or direct DB)."""
from typing import Dict, Any, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import KnowledgeRule
from app.database import supabase_db as sdb
import yaml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def _is_supabase(db: Any) -> bool:
    return hasattr(db, "table") and callable(getattr(db, "table", None))


class KnowledgeRulesService:
    """Service for working with ELMA365 knowledge rules."""

    def __init__(self, db: Union[AsyncSession, Any]):
        self._db = db
        self._supabase = db if _is_supabase(db) else None

    async def get_rule(self, rule_type: str) -> Optional[Dict[str, Any]]:
        """Get a rule by type."""
        if self._supabase:
            rule = await sdb.rule_get(self._supabase, rule_type)
            if rule:
                return {
                    "rule_type": rule["rule_type"],
                    "content": rule["content"],
                    "version": rule["version"],
                    "updated_at": rule["updated_at"][:24] if rule.get("updated_at") else None,
                    "updated_by": rule.get("updated_by"),
                }
            return None
        result = await self._db.execute(
            select(KnowledgeRule).where(KnowledgeRule.rule_type == rule_type)
        )
        rule = result.scalar_one_or_none()
        if rule:
            return {
                "rule_type": rule.rule_type,
                "content": rule.content,
                "version": rule.version,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
                "updated_by": rule.updated_by,
            }
        return None

    async def update_rule(
        self, rule_type: str, content: Dict[str, Any], updated_by: str
    ) -> Union[KnowledgeRule, Dict[str, Any]]:
        """Update or create a rule."""
        if self._supabase:
            existing = await sdb.rule_get(self._supabase, rule_type)
            version = (existing["version"] + 1) if existing else 1
            return await sdb.rule_upsert(
                self._supabase, rule_type, content, version, updated_by
            )
        result = await self._db.execute(
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
                updated_by=updated_by,
            )
            self._db.add(rule)
        await self._db.commit()
        await self._db.refresh(rule)
        return rule

    async def get_all_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get all rules."""
        if self._supabase:
            rules = await sdb.rules_list_all(self._supabase)
            return {
                r["rule_type"]: {
                    "content": r["content"],
                    "version": r["version"],
                    "updated_at": r["updated_at"][:24] if r.get("updated_at") else None,
                    "updated_by": r.get("updated_by"),
                }
                for r in rules
            }
        result = await self._db.execute(select(KnowledgeRule))
        rules = result.scalars().all()
        return {
            rule.rule_type: {
                "content": rule.content,
                "version": rule.version,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
                "updated_by": rule.updated_by,
            }
            for rule in rules
        }

    async def migrate_from_files(self, rules_dir: Path) -> Dict[str, int]:
        """Migrate rules from files to database (one-time operation)."""
        migrated = {}
        file_mapping = {
            "ARCHITECTURE_RULES_ELMA365.md": "architecture_rules",
            "PROCESS_RULES_ELMA365.md": "process_rules",
            "UI_RULES_ELMA365.md": "ui_rules",
            "elma365_arch_dictionary.yml": "dictionary",
            "ENGINEERING_PATTERNS_ELMA365.yml": "patterns",
        }
        for filename, rule_type in file_mapping.items():
            file_path = rules_dir / filename
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue
            try:
                if filename.endswith(".yml") or filename.endswith(".yaml"):
                    with open(file_path, "r", encoding="utf-8") as f:
                        content_dict = yaml.safe_load(f)
                    content = {"yaml": content_dict}
                else:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = {"text": f.read()}
                await self.update_rule(rule_type, content, "system")
                migrated[rule_type] = 1
                logger.info(f"Migrated {rule_type} from {filename}")
            except Exception as e:
                logger.error(f"Error migrating {filename}: {e}")
                migrated[rule_type] = 0
        return migrated
