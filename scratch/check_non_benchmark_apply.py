import asyncio
import sys
sys.path.insert(0, "backend")

from motor.motor_asyncio import AsyncIOMotorClient

async def check_missing_apply_live():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]

    # Check across all non-benchmark jobs
    cursor = db.jobs.find({
        "source": {"$ne": "curated_benchmark"},
        "$or": [
            {"apply_url": {"$in": [None, ""]}},
            {"is_direct_apply": {"$ne": True}},
            {"verification_status": {"$ne": "VERIFIED_ACTIVE"}},
        ]
    })
    items = await cursor.to_list(length=1000)
    print(f"Total non-benchmark jobs with missing apply, direct != True, or status != ACTIVE: {len(items)}")
    by_source = {}
    for it in items:
        src = it.get("source")
        status = it.get("verification_status")
        direct = it.get("is_direct_apply")
        has_url = bool(it.get("apply_url"))
        key = f"source={src}, status={status}, direct={direct}, has_url={has_url}"
        by_source[key] = by_source.get(key, 0) + 1

    for k, v in by_source.items():
        print(f"  {k}: {v}")

    # Now let's check: what about Bosch Group jobs specifically?
    # Are there ANY Bosch jobs where is_direct_apply is not True or apply_url is empty?
    bosch_odd = await db.jobs.find({
        "company": {"$regex": "Bosch", "$options": "i"},
        "$or": [
            {"apply_url": {"$in": [None, ""]}},
            {"is_direct_apply": {"$ne": True}},
            {"verification_status": {"$ne": "VERIFIED_ACTIVE"}},
        ]
    }).to_list(length=50)
    print(f"Bosch jobs with missing apply/direct: {len(bosch_odd)}")

    # What about Blueberry Labs?
    bb_odd = await db.jobs.find({
        "company": {"$regex": "Blueberry", "$options": "i"},
        "$or": [
            {"apply_url": {"$in": [None, ""]}},
            {"is_direct_apply": {"$ne": True}},
            {"verification_status": {"$ne": "VERIFIED_ACTIVE"}},
        ]
    }).to_list(length=50)
    print(f"Blueberry Labs jobs with missing apply/direct: {len(bb_odd)}")

if __name__ == "__main__":
    asyncio.run(check_missing_apply_live())
