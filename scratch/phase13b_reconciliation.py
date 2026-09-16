"""
Phase 13B: Comprehensive Post-Integration Verification & Reconciliation Script.
Gathers exact metrics from MongoDB, audits all 49 Indian records,
tests apply URLs, inspects deduplication, and analyzes the 28 unclassified records.
"""
import asyncio
import json
import re
import sys
import time
import httpx

sys.path.insert(0, r"c:\VINAY\roleradar\backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location
from app.modules.jobs.url_classifier import classify_application_url, ApplicationUrlType
from app.modules.jobs.verification import OpportunityLifecycleStatus
from app.modules.learning.role_taxonomy import resolve_role, ROLE_TAXONOMY


async def main():
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    db = client["roleradar"]
    coll = db[Collections.JOBS]

    print("=================================================================")
    print("PHASE 13B: INVENTORY RECONCILIATION & VERIFICATION AUDIT")
    print("=================================================================")

    # 1. GLOBAL INVENTORY BREAKDOWN
    print("\n--- 1. GLOBAL MONGO INVENTORY BY PROVIDER & CATEGORY ---")
    sources = ["smartrecruiters", "lever", "greenhouse", "adzuna", "ashby", "curated_benchmark", "curated", "custom"]
    global_metrics = {}

    for s in sources:
        tot = await coll.count_documents({"source": s})
        active = await coll.count_documents({"source": s, "verification_status": "VERIFIED_ACTIVE"})
        # India active: either country == India or is_india_opportunity is True
        india_act = await coll.count_documents({
            "source": s,
            "verification_status": "VERIFIED_ACTIVE",
            "$or": [{"country": "India"}, {"is_india_opportunity": True}],
        })
        internships = await coll.count_documents({
            "source": s,
            "verification_status": "VERIFIED_ACTIVE",
            "$or": [{"country": "India"}, {"is_india_opportunity": True}],
            "job_type": "internship",
        })
        ft = await coll.count_documents({
            "source": s,
            "verification_status": "VERIFIED_ACTIVE",
            "$or": [{"country": "India"}, {"is_india_opportunity": True}],
            "job_type": {"$ne": "internship"},
        })
        closed = await coll.count_documents({
            "source": s,
            "verification_status": {"$in": ["CLOSED", "EXPIRED", "STALE", "INVALID"]},
        })
        global_metrics[s] = {
            "total": tot,
            "active": active,
            "india_active": india_act,
            "internships": internships,
            "full_time": ft,
            "closed": closed,
        }
        print(f"  {s:18}: Total={tot:4} | Active={active:4} | India Active={india_act:4} (FT={ft:3}, Intern={internships:2}) | Inactive/Closed={closed:3}")

    # 2. ASHBY SPECIFIC INVENTORY RECONCILIATION
    print("\n--- 2. ASHBY INVENTORY ACCOUNTING ---")
    ashby_all = await coll.find({"source": "ashby"}).to_list(length=5000)
    print(f"Total Ashby Documents in MongoDB: {len(ashby_all)}")

    ashby_active = [j for j in ashby_all if j.get("verification_status") == "VERIFIED_ACTIVE"]
    ashby_closed = [j for j in ashby_all if j.get("verification_status") in ("CLOSED", "EXPIRED", "STALE", "INVALID")]
    
    # India filtering check
    ashby_india = []
    ashby_foreign = []
    for j in ashby_active:
        is_ind = j.get("is_india_opportunity", False) or j.get("country") == "India" or is_india_opportunity(j.get("location"))
        if is_ind:
            ashby_india.append(j)
        else:
            ashby_foreign.append(j)

    print(f"Ashby Active in MongoDB: {len(ashby_active)}")
    print(f"Ashby Inactive/Closed in MongoDB: {len(ashby_closed)}")
    print(f"Ashby India Active: {len(ashby_india)}")
    print(f"Ashby Foreign / Global Excluded: {len(ashby_foreign)}")

    # 3. AUDIT ALL 49 INDIAN ASHBY OPPORTUNITIES
    print("\n--- 3. DETAILED AUDIT OF ALL 49 INDIAN ASHBY OPPORTUNITIES ---")
    print(f"{'#':2} | {'Company':12} | {'Canonical Role':28} | {'Conf':4} | {'Title':40} | {'Location':25}")
    print("-" * 120)

    classified_records = []
    unclassified_records = []

    for idx, j in enumerate(ashby_india, 1):
        title = j.get("title", "")
        company = j.get("company", "")
        loc = j.get("location", "")
        apply_url = j.get("apply_url", "")
        source_id = j.get("source_job_id", "")
        prof, conf, reason = resolve_role(title)
        canon_role = prof.canonical_role if prof else "Unclassified / Specialized"
        
        row_info = {
            "index": idx,
            "id": j.get("id"),
            "source_job_id": source_id,
            "title": title,
            "company": company,
            "location": loc,
            "canonical_role": canon_role,
            "confidence": conf,
            "reason": reason,
            "apply_url": apply_url,
            "job_type": j.get("job_type"),
            "url_type": j.get("url_type"),
            "is_direct_apply": j.get("is_direct_apply"),
        }

        if prof and conf in ("HIGH", "MEDIUM"):
            classified_records.append(row_info)
        else:
            unclassified_records.append(row_info)

        print(f"{idx:2} | {company[:12]:12} | {canon_role[:28]:28} | {conf:4} | {title[:40]:40} | {loc[:25]:25}")

    print(f"\nClassified into Canonical Roles: {len(classified_records)}")
    print(f"Unclassified / Specialized: {len(unclassified_records)}")

    # 4. INSPECT THE 28 UNCLASSIFIED RECORDS
    print("\n--- 4. ANALYSIS OF THE 28 UNCLASSIFIED / SPECIALIZED RECORDS ---")
    for r in unclassified_records:
        print(f"  [{r['index']:2}] {r['company']:12} | Title: {r['title']}")
        print(f"       Reason: {r['reason']} | Loc: {r['location']}")

    # 5. TEST APPLY URL REACHABILITY VIA HTTP
    print("\n--- 5. LIVE HTTP APPLY URL TESTING ---")
    urls_to_test = [r["apply_url"] for r in (classified_records + unclassified_records)]
    
    tested = 0
    reachable = 0
    redirected = 0
    failed = 0
    invalid = 0

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as http_client:
        for u in urls_to_test:
            tested += 1
            if not u or not u.startswith("https://jobs.ashbyhq.com"):
                invalid += 1
                continue
            try:
                resp = await http_client.get(u, headers={"User-Agent": "RoleRadar-Audit/1.0"})
                if resp.status_code in (200, 201):
                    reachable += 1
                elif resp.status_code in (301, 302, 307, 308):
                    redirected += 1
                else:
                    print(f"  URL returned status {resp.status_code}: {u}")
                    failed += 1
            except Exception as e:
                print(f"  URL connection error: {u} -> {e}")
                failed += 1

    print(f"Tested: {tested} | Reachable (HTTP 200): {reachable} | Redirected: {redirected} | Failed: {failed} | Invalid: {invalid}")

    # 6. CROSS-PROVIDER DEDUPLICATION CHECK
    print("\n--- 6. CROSS-PROVIDER DEDUPLICATION CHECK ---")
    cross_duplicates = []
    for aj in ashby_india:
        a_comp = (aj.get("company") or "").lower().strip()
        a_title = (aj.get("title") or "").lower().strip()
        a_loc = (aj.get("location") or "").lower().strip()

        # Check in other providers
        match = await coll.find_one({
            "source": {"$ne": "ashby"},
            "company": {"$regex": f"^{re.escape(aj.get('company', ''))}$", "$options": "i"},
            "title": {"$regex": f"^{re.escape(aj.get('title', ''))}$", "$options": "i"},
            "verification_status": "VERIFIED_ACTIVE",
        })
        if match:
            cross_duplicates.append({"ashby": aj, "other": match})
            print(f"  Cross-provider duplicate found! Ashby ID: {aj['id']} vs Other ({match.get('source')}): {match['id']}")

    print(f"Total Cross-Provider Duplicates Found: {len(cross_duplicates)}")


if __name__ == "__main__":
    asyncio.run(main())
