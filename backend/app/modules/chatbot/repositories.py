"""
Persists Career Copilot multi-session conversations (Collections.CHAT_CONVERSATIONS).
Each document represents an independent conversation thread scoped to user_id.
Maintains full backward compatibility with legacy single-thread queries.
"""
from datetime import datetime, timezone
from typing import Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import Collections

MAX_STORED_MESSAGES = 100  # keep messages per conversation bounded


def _doc_to_dict(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "user_id": doc.get("user_id"),
        "title": doc.get("title", "New Conversation"),
        "messages": doc.get("messages", []),
        "created_at": doc.get("created_at", datetime.now(timezone.utc)).isoformat() if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at")),
        "updated_at": doc.get("updated_at", datetime.now(timezone.utc)).isoformat() if isinstance(doc.get("updated_at"), datetime) else str(doc.get("updated_at")),
    }


def _derive_title(message_text: str) -> str:
    """Derives a concise, readable title from the first user prompt."""
    clean = message_text.strip().replace("\n", " ")
    if len(clean) > 40:
        return clean[:37] + "..."
    return clean or "New Chat"


# ------------------------------------------------------------------
# Backward Compatible Helpers (Legacy single-thread tests & endpoints)
# ------------------------------------------------------------------
async def get_conversation(db: AsyncIOMotorDatabase | Any, user_id: str) -> list[dict]:
    """Legacy helper: returns the messages list of the user's active conversation."""
    thread = await get_conversation_thread(db, user_id)
    return thread.get("messages", []) if thread else []


async def clear_conversation(db: AsyncIOMotorDatabase | Any, user_id: str) -> None:
    """Legacy helper: clears all conversations for user."""
    await db[Collections.CHAT_CONVERSATIONS].delete_many({"user_id": user_id})


async def append_messages(db: AsyncIOMotorDatabase | Any, user_id: str, new_messages: list[dict]) -> None:
    """Legacy helper: appends messages to user's active conversation."""
    await append_messages_to_conversation(db, user_id, None, new_messages)


# ------------------------------------------------------------------
# Multi-Session Conversation Threads
# ------------------------------------------------------------------
async def list_conversations(db: AsyncIOMotorDatabase | Any, user_id: str) -> list[dict]:
    """Returns a list of conversation summaries for the user, ordered by latest activity."""
    cursor = db[Collections.CHAT_CONVERSATIONS].find({"user_id": user_id}).sort("updated_at", -1)
    results = []
    async for doc in cursor:
        msgs = doc.get("messages", [])
        last_msg = msgs[-1]["text"] if msgs else ""
        preview = (last_msg[:60] + "...") if len(last_msg) > 60 else last_msg
        results.append({
            "id": str(doc["_id"]),
            "title": doc.get("title", "New Conversation"),
            "message_count": len(msgs),
            "last_preview": preview,
            "created_at": doc.get("created_at", datetime.now(timezone.utc)).isoformat() if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at")),
            "updated_at": doc.get("updated_at", datetime.now(timezone.utc)).isoformat() if isinstance(doc.get("updated_at"), datetime) else str(doc.get("updated_at")),
        })
    return results


async def create_conversation(
    db: AsyncIOMotorDatabase | Any, user_id: str, title: str | None = None, initial_messages: list[dict] | None = None
) -> dict:
    """Creates a new conversation thread."""
    now = datetime.now(timezone.utc)
    msgs = initial_messages or []
    conv_title = title or (_derive_title(msgs[0]["text"]) if msgs else "New Chat")
    
    doc = {
        "user_id": user_id,
        "title": conv_title,
        "messages": msgs,
        "created_at": now,
        "updated_at": now,
    }
    result = await db[Collections.CHAT_CONVERSATIONS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _doc_to_dict(doc)


async def get_conversation_thread(
    db: AsyncIOMotorDatabase | Any, user_id: str, conv_id: str | None = None
) -> dict | None:
    """Fetches a specific conversation thread document or the latest active conversation."""
    if conv_id:
        try:
            oid = ObjectId(conv_id)
            doc = await db[Collections.CHAT_CONVERSATIONS].find_one({"_id": oid, "user_id": user_id})
            return _doc_to_dict(doc) if doc else None
        except Exception:
            return None

    # Fallback to latest conversation
    doc = await db[Collections.CHAT_CONVERSATIONS].find_one({"user_id": user_id}, sort=[("updated_at", -1)])
    if doc:
        return _doc_to_dict(doc)
    return None


async def append_messages_to_conversation(
    db: AsyncIOMotorDatabase | Any, user_id: str, conv_id: str | None, new_messages: list[dict]
) -> dict:
    """Appends messages to a conversation thread, auto-generating a title from the first prompt if needed."""
    now = datetime.now(timezone.utc)
    conv = await get_conversation_thread(db, user_id, conv_id)
    
    if not conv:
        first_user_msg = next((m["text"] for m in new_messages if m.get("role") == "user"), "New Chat")
        title = _derive_title(first_user_msg)
        return await create_conversation(db, user_id, title=title, initial_messages=new_messages)

    existing_msgs = conv.get("messages", [])
    combined = (existing_msgs + new_messages)[-MAX_STORED_MESSAGES:]
    
    update_fields: dict = {"messages": combined, "updated_at": now}
    
    if conv.get("title") in ("New Chat", "New Conversation"):
        first_user_msg = next((m["text"] for m in (existing_msgs + new_messages) if m.get("role") == "user"), None)
        if first_user_msg:
            update_fields["title"] = _derive_title(first_user_msg)

    oid = ObjectId(conv["id"])
    await db[Collections.CHAT_CONVERSATIONS].update_one(
        {"_id": oid, "user_id": user_id},
        {"$set": update_fields}
    )
    
    conv["messages"] = combined
    conv["updated_at"] = now.isoformat()
    if "title" in update_fields:
        conv["title"] = update_fields["title"]
    return conv


async def update_conversation_title(
    db: AsyncIOMotorDatabase | Any, user_id: str, conv_id: str, new_title: str
) -> bool:
    """Renames a conversation thread."""
    try:
        oid = ObjectId(conv_id)
        res = await db[Collections.CHAT_CONVERSATIONS].update_one(
            {"_id": oid, "user_id": user_id},
            {"$set": {"title": new_title.strip()[:100], "updated_at": datetime.now(timezone.utc)}}
        )
        return res.matched_count > 0
    except Exception:
        return False


async def delete_conversation(
    db: AsyncIOMotorDatabase | Any, user_id: str, conv_id: str
) -> bool:
    """Deletes a specific conversation thread."""
    try:
        oid = ObjectId(conv_id)
        res = await db[Collections.CHAT_CONVERSATIONS].delete_one({"_id": oid, "user_id": user_id})
        return res.deleted_count > 0
    except Exception:
        return False


async def clear_all_conversations(db: AsyncIOMotorDatabase | Any, user_id: str) -> None:
    """Clears all conversations for the given user."""
    await db[Collections.CHAT_CONVERSATIONS].delete_many({"user_id": user_id})
