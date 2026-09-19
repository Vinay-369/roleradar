import asyncio
import sys
import json
sys.path.insert(0, "backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.location_normalization import is_india_opportunity

async def investigate():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    coll = db[Collections.JOBS]

    # Query all active Indian opportunities
    cursor = coll.find({"verification_status": "VERIFIED_ACTIVE"})
    all_active = await cursor.to_list(length=10000)

    indian_active = [
        o for o in all_active
        if o.get("country") == "India" or is_india_opportunity(o.get("location", ""), o.get("description", ""))
    ]

    print(f"Total Indian Active: {len(indian_active)}")

    # 1. Inspect all internships
    internships = [o for o in indian_active if o.get("opportunity_type") == "INTERNSHIP" or o.get("job_type") == "internship"]
    print(f"Total Internships: {len(internships)}")
    for idx, i in enumerate(internships, 1):
        print(f"[{idx}] ID: {i['id']} | Provider: {i.get('source')} | Co: {i.get('company')} | Title: {i.get('title')} | opp_type: {i.get('opportunity_type')} | job_type: {i.get('job_type')}")

    # 2. Inspect the 5 numeric salary records
    numeric_salaries = [o for o in indian_active if (o.get("salary_min") and o.get("salary_min") > 0) or (o.get("salary_max") and o.get("salary_max") > 0)]
    print(f"\nNumeric Salaries Found: {len(numeric_salaries)}")
    for idx, s in enumerate(numeric_salaries, 1):
        print(f"\n--- Numeric Salary [{idx}] ---")
        print("ID:", s["id"])
        print("Company:", s.get("company"))
        print("Title:", s.get("title"))
        print("salary_min:", s.get("salary_min"), "salary_max:", s.get("salary_max"))
        print("compensation_text:", s.get("compensation_text"))
        print("compensation_type:", s.get("compensation_type"))
        print("apply_url:", s.get("apply_url"))
        print("source_url:", s.get("source_url"))
        # Search description for the number
        desc = s.get("description", "")
        print("Description snippet around match:")
        for line in desc.split("\n"):
            if any(term in line.lower() for term in ["lakh", "lpa", "ctc", "salary", "inr", "rs", "5", "lac"]):
                print("  LINE:", line[:120])

    # 3. Inspect the 23 VERIFIED_PARTIAL records
    partials = [o for o in indian_active if o.get("completeness_status") == "VERIFIED_PARTIAL"]
    print(f"\nVERIFIED_PARTIAL Records: {len(partials)}")
    for idx, p in enumerate(partials, 1):
        print(f"[{idx}] ID: {p['id']} | Provider: {p.get('source')} | Co: {p.get('company')} | Title: {p.get('title')} | DescLen: {len(p.get('description', ''))} | Resps: {len(p.get('responsibilities', []))} | Quals: {len(p.get('qualifications', []))} | Skills: {len(p.get('skills_required', []))}")

if __name__ == "__main__":
    asyncio.run(investigate())
