import asyncio
import json
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

    cursor = db[Collections.JOBS].find(query)
    docs = await cursor.to_list(length=1000)
    print(f"Total audited documents: {len(docs)}")

    by_provider = {"smartrecruiters": [], "lever": [], "greenhouse": []}
    for doc in docs:
        by_provider[doc.get("source", "other")].append(doc)

    opp_types = {}
    for doc in docs:
        ot = str(doc.get("opportunity_type"))
        opp_types[ot] = opp_types.get(ot, 0) + 1
    print("Opportunity Types:", opp_types)

    # Inspect field population counts
    fields = [
        "title", "company", "location", "opportunity_type", "description",
        "responsibilities", "qualifications", "skills_required", "skills_nice_to_have",
        "experience_min", "experience_max", "salary_min", "salary_max",
        "stipend_min", "stipend_max", "compensation_text", "internship_duration_months",
        "apply_url", "is_direct_apply", "workplace_type"
    ]

    stats = {f: 0 for f in fields}
    for doc in docs:
        for f in fields:
            val = doc.get(f)
            if val not in (None, "", [], {}):
                stats[f] += 1

    print("\nField Presence across all 587 opportunities:")
    for f, count in stats.items():
        pct = (count / len(docs)) * 100
        print(f"  {f:28}: {count:4d} / {len(docs)} ({pct:5.1f}%)")

    # Inspect provider breakdown
    print("\nProvider breakdown:")
    for prov, pdocs in by_provider.items():
        interns = sum(1 for d in pdocs if str(d.get("opportunity_type")).upper() == "INTERNSHIP" or d.get("is_internship"))
        jobs = len(pdocs) - interns
        print(f"  {prov:18}: total={len(pdocs)}, jobs={jobs}, internships={interns}")

if __name__ == "__main__":
    asyncio.run(main())
