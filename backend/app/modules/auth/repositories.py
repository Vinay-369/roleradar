"""
Data access for the `users` collection. Routes/services never touch
Motor directly — they go through here, so the query shape is defined
in exactly one place.
"""
from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import Collections


async def get_user_by_email(db: AsyncIOMotorDatabase, email: str) -> dict | None:
    return await db[Collections.USERS].find_one({"email": email})


async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> dict | None:
    try:
        oid = ObjectId(user_id)
    except Exception:
        return None
    return await db[Collections.USERS].find_one({"_id": oid})


async def create_user(db: AsyncIOMotorDatabase, email: str, password_hash: str, full_name: str, phone: str | None) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "email": email,
        "password_hash": password_hash,
        "full_name": full_name,
        "phone": phone,
        "onboarding_completed": False,
        "created_at": now,
        "updated_at": now,
    }
    result = await db[Collections.USERS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc
