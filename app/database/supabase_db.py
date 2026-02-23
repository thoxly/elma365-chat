"""Supabase API helpers (run sync client calls in thread to not block event loop)."""
import asyncio
from typing import Any, Dict, List, Optional

# Supabase client type (sync)
Client = Any


async def _run_sync(sync_fn):
    return await asyncio.to_thread(sync_fn)


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


# --- chat_messages ---

async def message_insert(sb: Client, row: Dict[str, Any]) -> Dict[str, Any]:
    r = await _run_sync(lambda: sb.table("chat_messages").insert(row).select().single().execute())
    return r.data


async def messages_list(sb: Client, user_id: str, session_id: str) -> List[Dict[str, Any]]:
    r = await _run_sync(
        lambda: sb.table("chat_messages")
        .select("*")
        .eq("user_id", user_id)
        .eq("session_id", session_id)
        .order("created_at")
        .execute()
    )
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
