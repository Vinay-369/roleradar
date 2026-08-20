from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import Collections


async def get_profile(db: AsyncIOMotorDatabase, user_id: str) -> dict | None:
    return await db[Collections.PROFILES].find_one({"user_id": user_id})


async def upsert_profile(db: AsyncIOMotorDatabase, user_id: str, data: dict) -> dict:
    now = datetime.now(timezone.utc)
    data = {**data, "user_id": user_id, "consent_timestamp": now, "updated_at": now}
    await db[Collections.PROFILES].update_one(
        {"user_id": user_id},
        {"$set": data, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return await get_profile(db, user_id)
