import asyncio
import sys
sys.path.insert(0, "backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.modules.jobs import services as jobs_services
from app.core.config import get_settings

async def audit_all_jobs():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]

    # 1. Total count of all opportunities in db.jobs
    total_jobs = await db.jobs.count_documents({})
    print(f"Total jobs in DB: {total_jobs}")

    # 2. Check each source breakdown
    sources = await db.jobs.distinct("source")
    for s in sources:
        cnt = await db.jobs.count_documents({"source": s})
        active_cnt = await db.jobs.count_documents({"source": s, "verification_status": "VERIFIED_ACTIVE"})
        direct_cnt = await db.jobs.count_documents({"source": s, "is_direct_apply": True})
        has_url = await db.jobs.count_documents({"source": s, "apply_url": {"$regex": "^https?://"}})
        print(f"Source: {s:20s} | total={cnt:5d} | active={active_cnt:5d} | direct={direct_cnt:5d} | has_url={has_url:5d}")

    # 3. Are there ANY live jobs (smartrecruiters, lever, greenhouse) where:
    # - apply_url is empty
    # - is_direct_apply is False
    # - verification_status != VERIFIED_ACTIVE
    print("\nChecking live ATS jobs with anomalies:")
    anomalous = await db.jobs.find({
        "source": {"$in": ["smartrecruiters", "lever", "greenhouse"]},
        "$or": [
            {"apply_url": {"$not": {"$regex": "^https?://"}}},
            {"is_direct_apply": False},
            {"verification_status": {"$ne": "VERIFIED_ACTIVE"}},
        ]
    }).to_list(length=100)
    print(f"Anomalous live ATS jobs: {len(anomalous)}")
    for a in anomalous[:15]:
        print(f"  [{a.get('source')}] {a.get('id')} - {a.get('company')} - {a.get('title')}")
        print(f"     apply_url: {a.get('apply_url')}")
        print(f"     is_direct: {a.get('is_direct_apply')}, status: {a.get('verification_status')}")

    # 4. What about Blueberry Labs jobs specifically?
    print("\nChecking Blueberry Labs jobs:")
    bb = await db.jobs.find({"company": {"$regex": "Blueberry", "$options": "i"}}).to_list(length=20)
    print(f"Blueberry Labs count: {len(bb)}")
    for b in bb:
        print(f"  {b.get('id')} - {b.get('title')} - apply_url: {b.get('apply_url')} - is_direct: {b.get('is_direct_apply')} - status: {b.get('verification_status')}")

    # 5. What about Bosch Group jobs specifically?
    print("\nChecking Bosch Group jobs count:")
    bosch_cnt = await db.jobs.count_documents({"company": {"$regex": "Bosch", "$options": "i"}})
    print(f"Bosch jobs count: {bosch_cnt}")

if __name__ == "__main__":
    asyncio.run(audit_all_jobs())
