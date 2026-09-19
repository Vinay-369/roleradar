import asyncio
import sys
import json
sys.path.insert(0, "backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.completeness import evaluate_opportunity_completeness

async def inspect_partials():
    client = AsyncIOMotorClient(get_settings().MONGO_URI)
    db = client[get_settings().MONGO_DB_NAME]
    coll = db[Collections.JOBS]

    cursor = coll.find({"completeness_status": "VERIFIED_PARTIAL"})
    partials = await cursor.to_list(100)

    print(f"Total VERIFIED_PARTIAL: {len(partials)}")

    report_list = []
    for idx, p in enumerate(partials, 1):
        res = evaluate_opportunity_completeness(p)
        desc = p.get("description", "")
        item = {
            "index": idx,
            "id": p["id"],
            "provider": p.get("source"),
            "company": p.get("company"),
            "title": p.get("title"),
            "opportunity_type": p.get("opportunity_type"),
            "desc_len": len(desc),
            "desc_text": desc,
            "raw_html": p.get("raw_html", "")[:200],
            "apply_url": p.get("apply_url"),
            "responsibilities": p.get("responsibilities", []),
            "qualifications": p.get("qualifications", []),
            "skills_required": p.get("skills_required", []),
            "experience_min": p.get("experience_min"),
            "experience_max": p.get("experience_max"),
            "salary_disclosed": p.get("salary_disclosed"),
            "missing_required": res.missing_required_information,
            "source_completeness": res.source_completeness.value,
            "quality": res.recommendation_quality.value,
            "available_info": res.available_information,
        }
        report_list.append(item)
        print(f"\n[{idx}] {p['id']} | {p.get('company')} | {p.get('title')}")
        print(f"     Desc (len {len(desc)}): {desc}")
        print(f"     Missing: {res.missing_required_information}")
        print(f"     Available: {res.available_information}")

    with open("scratch/partials_detail.json", "w", encoding="utf-8") as f:
        json.dump(report_list, f, indent=2)

if __name__ == "__main__":
    asyncio.run(inspect_partials())
