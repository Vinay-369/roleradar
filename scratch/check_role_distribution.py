import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.learning.role_taxonomy import resolve_role
from app.modules.jobs.location_normalization import is_india_opportunity

async def main():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    coll = db[Collections.JOBS]

    cursor = coll.find({"verification_status": "VERIFIED_ACTIVE"})
    all_active = await cursor.to_list(10000)
    
    indian_active = [
        o for o in all_active
        if o.get("country") == "India" or is_india_opportunity(o.get("location", ""), o.get("description", ""))
    ]
    
    # Check roles distribution
    roles = {}
    for d in indian_active:
        if d.get("external_id") == "gh_inmobi_8138503":
            continue
        r = d.get("canonical_role")
        roles[r] = roles.get(r, 0) + 1
        
    print(f"Total unique active Indian: {sum(roles.values())}")
    print("Role distribution:")
    for r, count in sorted(roles.items(), key=lambda x: -x[1]):
        print(f"  {r}: {count}")

if __name__ == "__main__":
    asyncio.run(main())
