import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections

async def main():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    query = {
        "verification_status": "VERIFIED_ACTIVE",
        "country": "India",
        "source": {"$in": ["smartrecruiters", "lever", "greenhouse"]}
    }

    docs = await db[Collections.JOBS].find(query).to_list(1000)
    print(f"Total Live Indian Opportunities: {len(docs)}")

    internships = [d for d in docs if d.get("job_type") == "internship" or d.get("opportunity_type") == "INTERNSHIP" or "intern" in (d.get("title") or "").lower()]
    print(f"Detected Internships Count: {len(internships)}")
    for d in internships:
        print(f"  [{d.get('source')}] {d.get('company')}: {d.get('title')} (job_type={d.get('job_type')}, opp_type={d.get('opportunity_type')})")

    # Inspect companies per provider
    sr_companies = set(d.get("company") for d in docs if d.get("source") == "smartrecruiters")
    lev_companies = set(d.get("company") for d in docs if d.get("source") == "lever")
    gh_companies = set(d.get("company") for d in docs if d.get("source") == "greenhouse")

    print("\nSmartRecruiters Companies in DB:", len(sr_companies), sr_companies)
    print("Lever Companies in DB:", len(lev_companies), lev_companies)
    print("Greenhouse Companies in DB:", len(gh_companies), gh_companies)

if __name__ == "__main__":
    asyncio.run(main())
