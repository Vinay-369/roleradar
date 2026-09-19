import asyncio
import sys
sys.path.insert(0, "backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.location_normalization import is_india_opportunity

async def check():
    client = AsyncIOMotorClient(get_settings().MONGO_URI)
    db = client[get_settings().MONGO_DB_NAME]
    
    cursor = db[Collections.JOBS].find({"verification_status": "VERIFIED_ACTIVE"})
    all_active = await cursor.to_list(10000)
    
    indian_active = [
        o for o in all_active
        if o.get("country") == "India" or is_india_opportunity(o.get("location", ""), o.get("description", ""))
    ]
    
    internships = [o for o in indian_active if o.get("opportunity_type") == "INTERNSHIP" or o.get("job_type") == "internship"]
    jobs = [o for o in indian_active if o not in internships]
    
    print(f"Total Indian Active: {len(indian_active)}")
    print(f"Total Jobs: {len(jobs)}")
    print(f"Total Internships: {len(internships)}")
    print(f"Sum: {len(jobs) + len(internships)}")

    for idx, i in enumerate(internships, 1):
        print(f"\n[{idx}] ID: {i['id']}")
        print(f"    Provider: {i.get('source')}")
        print(f"    Company: {i.get('company')}")
        print(f"    Title: {i.get('title')}")
        print(f"    Source URL: {i.get('source_url')}")
        print(f"    Apply URL: {i.get('apply_url')}")
        print(f"    opportunity_type: {i.get('opportunity_type')}")
        print(f"    job_type: {i.get('job_type')}")
        print(f"    completeness_status: {i.get('completeness_status')}")

if __name__ == "__main__":
    asyncio.run(check())
