import asyncio
import sys
sys.path.insert(0, "backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.providers import CuratedJobProvider
from app.modules.jobs.location_normalization import is_india_opportunity

async def compare():
    client = AsyncIOMotorClient(get_settings().MONGO_URI)
    db = client[get_settings().MONGO_DB_NAME]
    coll = db[Collections.JOBS]
    curated = CuratedJobProvider(db)

    # Method 1: Curated search (as in authoritative_db_audit.py)
    # Note: we added {"completeness_status": {"$ne": "INSUFFICIENT"}} to CuratedJobProvider!
    search_res = await curated.search({"limit": 1000, "skip": 0, "region": "india", "active_discovery_only": True, "direct_apply_only": True})
    print("Curated.search returned:", len(search_res))

    # Method 2: Curated search with include_insufficient
    search_with_insufficient = await curated.search({"limit": 1000, "skip": 0, "region": "india", "active_discovery_only": True, "direct_apply_only": True, "include_insufficient": True})
    print("Curated.search with include_insufficient returned:", len(search_with_insufficient))

    # Method 3: Direct MongoDB query on VERIFIED_ACTIVE Indian
    cursor = coll.find({"verification_status": "VERIFIED_ACTIVE"})
    all_active = await cursor.to_list(10000)
    indian_active = [
        o for o in all_active
        if o.get("country") == "India" or is_india_opportunity(o.get("location", ""), o.get("description", ""))
    ]
    print("Direct Mongo Indian VERIFIED_ACTIVE:", len(indian_active))

    ids_search = {j["id"] for j in search_res}
    ids_active = {j["id"] for j in indian_active}

    diff_1 = ids_active - ids_search
    print("In direct Mongo but not in curated.search:", len(diff_1), diff_1)

    diff_2 = ids_search - ids_active
    print("In curated.search but not in direct Mongo:", len(diff_2), diff_2)

if __name__ == "__main__":
    asyncio.run(compare())
