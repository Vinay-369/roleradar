import asyncio
import json
import re
import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
sys.stdout.reconfigure(encoding="utf-8")

from motor.motor_asyncio import AsyncIOMotorClient
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role, RoleCompetencyProfile

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]
    coll = db["jobs"]

    primary_jobs = await coll.find({
        "country": "India",
        "verification_status": "VERIFIED_ACTIVE",
        "completeness_status": "VERIFIED_COMPLETE"
    }).to_list(length=None)

    print(f"Total Primary Recommendations in MongoDB: {len(primary_jobs)}")

    # 1. Baseline: resolve_role with just title
    title_matched = 0
    unmatched = []
    
    for idx, j in enumerate(primary_jobs):
        title = j.get("title") or ""
        print(f"[{idx+1}/{len(primary_jobs)}] Evaluating: {title}", flush=True)
        prof, conf, reason = resolve_role(title)
        if prof and conf in ("HIGH", "MEDIUM"):
            title_matched += 1
        else:
            unmatched.append(j)

    print(f"Direct Title Matches: {title_matched}")
    print(f"Unmatched / Specialized: {len(unmatched)}")

    # Let's inspect what titles are in unmatched
    print("\nSample of Unmatched Titles (first 25):")
    for u in unmatched[:25]:
        print(f"  ID: {u.get('id')} | Company: {u.get('company')} | Title: {u.get('title')}")

if __name__ == "__main__":
    asyncio.run(main())
