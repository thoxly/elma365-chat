"""Supabase API helpers (run sync client calls in thread to not block event loop)."""
import asyncio
import logging
from typing import Any, Dict, List, Optional

# Supabase client type (sync)
Client = Any
logger = logging.getLogger(__name__)


async def _run_sync(sync_fn):
    """Run sync Supabase call in thread; re-raise with clear message for logs."""
    try:
        return await asyncio.to_thread(sync_fn)
    except Exception as e:
        msg = f"Supabase API error: {type(e).__name__}: {e}"
        logger.error("%s", msg, exc_info=True)
        raise RuntimeError(msg) from e


# --- task_templates ---

async def template_get(sb: Client, template_id: int) -> Optional[Dict[str, Any]]:
    r = await _run_sync(
        lambda: sb.table("task_templates").select("*").eq("id", template_id).maybe_single().execute()
    )
    return r.data if r.data else None


async def template_list(sb: Client) -> List[Dict[str, Any]]:
    r = await _run_sync(
        lambda: sb.table("task_templates").select("*").order("created_at", desc=True).execute()
    )
    return r.data or []


async def template_create(sb: Client, row: Dict[str, Any]) -> Dict[str, Any]:
    r = await _run_sync(lambda: sb.table("task_templates").insert(row).select().single().execute())
    return r.data


async def template_update(sb: Client, template_id: int, row: Dict[str, Any]) -> Dict[str, Any]:
    r = await _run_sync(
        lambda: sb.table("task_templates").update(row).eq("id", template_id).select().single().execute()
    )
    return r.data


async def template_delete(sb: Client, template_id: int) -> None:
    await _run_sync(lambda: sb.table("task_templates").delete().eq("id", template_id).execute())


# --- chat_sessions ---

async def sessions_list(sb: Client, user_id: str) -> List[Dict[str, Any]]:
    logger.debug("supabase_db.sessions_list: user_id=%s table=chat_sessions", user_id)
    r = await _run_sync(
        lambda: sb.table("chat_sessions")
        .select("session_id, title, created_at, updated_at")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    logger.debug("supabase_db.sessions_list: got %s rows", len(r.data or []))
    return r.data or []


async def session_upsert(sb: Client, user_id: str, session_id: str, title_for_new: Optional[str] = None) -> Dict[str, Any]:
    """Создать сессию если нет; при создании задать title_for_new, при существующей не менять title."""
    logger.debug("supabase_db.session_upsert: user_id=%s session_id=%s table=chat_sessions", user_id, session_id)
    r_existing = await _run_sync(
        lambda: sb.table("chat_sessions").select("*").eq("session_id", session_id).eq("user_id", user_id).maybe_single().execute()
    )
    if r_existing.data:
        logger.debug("supabase_db.session_upsert: existing session found")
        return r_existing.data
    r = await _run_sync(
        lambda: sb.table("chat_sessions")
        .insert({"session_id": session_id, "user_id": user_id, "title": title_for_new or "Новый чат"})
        .select()
        .single()
        .execute()
    )
    logger.debug("supabase_db.session_upsert: inserted new session")
    return r.data


async def session_update_title(sb: Client, user_id: str, session_id: str, title: str) -> Optional[Dict[str, Any]]:
    r = await _run_sync(
        lambda: sb.table("chat_sessions")
        .update({"title": title})
        .eq("session_id", session_id)
        .eq("user_id", user_id)
        .select()
        .maybe_single()
        .execute()
    )
    return r.data if r.data else None


# --- chat_messages ---

async def message_insert(sb: Client, row: Dict[str, Any]) -> Dict[str, Any]:
    r = await _run_sync(lambda: sb.table("chat_messages").insert(row).select().single().execute())
    return r.data


async def messages_list(sb: Client, user_id: str, session_id: str) -> List[Dict[str, Any]]:
    logger.debug("supabase_db.messages_list: user_id=%s session_id=%s table=chat_messages", user_id, session_id)
    r = await _run_sync(
        lambda: sb.table("chat_messages")
        .select("*")
        .eq("user_id", user_id)
        .eq("session_id", session_id)
        .order("created_at")
        .execute()
    )
    logger.debug("supabase_db.messages_list: got %s rows", len(r.data or []))
    return r.data or []


# --- chat_documents ---

async def document_insert(sb: Client, row: Dict[str, Any]) -> Dict[str, Any]:
    r = await _run_sync(lambda: sb.table("chat_documents").insert(row).select().single().execute())
    return r.data


async def documents_list(sb: Client, user_id: str, session_id: str) -> List[Dict[str, Any]]:
    r = await _run_sync(
        lambda: sb.table("chat_documents")
        .select("*")
        .eq("user_id", user_id)
        .eq("session_id", session_id)
        .execute()
    )
    return r.data or []


# --- knowledge_rules ---

async def rule_get(sb: Client, rule_type: str) -> Optional[Dict[str, Any]]:
    r = await _run_sync(
        lambda: sb.table("knowledge_rules").select("*").eq("rule_type", rule_type).maybe_single().execute()
    )
    return r.data if r.data else None


async def rule_upsert(sb: Client, rule_type: str, content: Dict[str, Any], version: int, updated_by: str) -> Dict[str, Any]:
    existing = await rule_get(sb, rule_type)
    if existing:
        r = await _run_sync(
            lambda: sb.table("knowledge_rules")
            .update({"content": content, "version": version, "updated_by": updated_by})
            .eq("rule_type", rule_type)
            .select()
            .single()
            .execute()
        )
        return r.data
    r = await _run_sync(
        lambda: sb.table("knowledge_rules")
        .insert({"rule_type": rule_type, "content": content, "version": version, "updated_by": updated_by})
        .select()
        .single()
        .execute()
    )
    return r.data


async def rules_list_all(sb: Client) -> List[Dict[str, Any]]:
    r = await _run_sync(lambda: sb.table("knowledge_rules").select("*").execute())
    return r.data or []
