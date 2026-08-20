"""
Persists Career Copilot conversations (Collections.CHAT_CONVERSATIONS)
so history survives a page refresh/new session, per the reported gap.
One document per user holding an ordered message list -- simple and
sufficient at this scale; a message-per-document design would only be
worth it at much higher volume.
"""
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import Collections

MAX_STORED_MESSAGES = 100  # keep the doc bounded; oldest messages drop off


async def get_conversation(db: AsyncIOMotorDatabase, user_id: str) -> list[dict]:
    doc = await db[Collections.CHAT_CONVERSATIONS].find_one({"user_id": user_id})
    return doc["messages"] if doc else []


async def append_messages(db: AsyncIOMotorDatabase, user_id: str, new_messages: list[dict]) -> None:
    now = datetime.now(timezone.utc)
    existing = await get_conversation(db, user_id)
    combined = (existing + new_messages)[-MAX_STORED_MESSAGES:]
    await db[Collections.CHAT_CONVERSATIONS].update_one(
        {"user_id": user_id},
        {"$set": {"messages": combined, "updated_at": now}, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )


async def clear_conversation(db: AsyncIOMotorDatabase, user_id: str) -> None:
    await db[Collections.CHAT_CONVERSATIONS].delete_one({"user_id": user_id})
