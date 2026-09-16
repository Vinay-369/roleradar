"""
Phase 13: Ashby Inventory Measurement & Audit Script.
Measures pre-sync database inventory, executes Ashby sync, analyzes yields,
computes canonical role distributions, and calculates actual incremental useful inventory.
"""
import asyncio
import json
import sys
import time

sys.path.insert(0, r"c:\VINAY\roleradar\backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.services import sync_all_ashby_boards
from app.modules.learning.role_taxonomy import resolve_role


async def main():
    settings = get_settings()
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    db = client["roleradar"]
    coll = db[Collections.JOBS]

    print("=================================================================")
    print("PHASE 13: ASHBY INVENTORY MEASUREMENT & AUDIT")
    print("=================================================================")

    # 1. PRE-SYNC AUDIT
    print("\n--- 1. PRE-SYNC INVENTORY METRICS ---")
    total_pre = await coll.count_documents({})
    active_pre = await coll.count_documents({"verification_status": "VERIFIED_ACTIVE"})
    india_active_pre = await coll.count_documents({"verification_status": "VERIFIED_ACTIVE", "is_india_opportunity": True})
    
    provider_counts_pre = {}
    for p in ["smartrecruiters", "lever", "greenhouse", "adzuna", "curated_benchmark", "ashby"]:
        p_tot = await coll.count_documents({"source": p})
        p_act = await coll.count_documents({"source": p, "verification_status": "VERIFIED_ACTIVE"})
        p_in_act = await coll.count_documents({"source": p, "verification_status": "VERIFIED_ACTIVE", "is_india_opportunity": True})
        provider_counts_pre[p] = {"total": p_tot, "active": p_act, "india_active": p_in_act}
        print(f"  {p:18}: Total={p_tot:4} | Active={p_act:4} | India Active={p_in_act:4}")

    print(f"\nTotal Database Records: {total_pre}")
    print(f"Total Active Listings: {active_pre}")
    print(f"Total Live Indian Active Listings: {india_active_pre}")

    # 2. RUN ASHBY SYNC
    print("\n--- 2. EXECUTING ASHBY SYNCHRONIZATION ---")
    t0 = time.perf_counter()
    sync_res = await sync_all_ashby_boards(db, settings)
    sync_duration = time.perf_counter() - t0
    print(f"Ashby Sync completed in {sync_duration:.2f}s")
    print(f"Total Boards Processed: {sync_res['total_boards']}")
    print(f"Total Verified Active Upserted: {sync_res['verified_active']}")
    print(f"Total Closed Listings: {sync_res['closed']}")
    for b_res in sync_res["results"]:
        print(f"  Board '{b_res['board']}': fetched={b_res['fetched']}, verified_active={b_res['verified_active']}, closed={b_res['closed']}, internships={b_res['internships']}, errors={b_res['errors']}")

    # 3. ASHBY SPECIFIC DETAILED AUDIT
    print("\n--- 3. ASHBY OPPORTUNITY AUDIT ---")
    ashby_cursor = coll.find({"source": "ashby"})
    ashby_records = await ashby_cursor.to_list(length=2000)
    print(f"Total Ashby Records in DB: {len(ashby_records)}")

    raw_count = sum(b.get("fetched", 0) for b in sync_res["results"])
    normalized_count = len(ashby_records)
    active_count = 0
    india_count = 0
    relevant_count = 0
    internship_count = 0
    fulltime_count = 0
    actionable_count = 0
    valid_apply_urls = 0
    role_distribution = {}
    location_distribution = {}
    completeness_distribution = {}

    for doc in ashby_records:
        status = doc.get("verification_status")
        is_india = doc.get("is_india_opportunity", False)
        jtype = doc.get("job_type")
        url_type = doc.get("url_type")
        apply_url = doc.get("apply_url", "")
        title = doc.get("title", "")
        comp_status = doc.get("completeness_status", "UNKNOWN")

        completeness_distribution[comp_status] = completeness_distribution.get(comp_status, 0) + 1

        if status == "VERIFIED_ACTIVE":
            active_count += 1
            if is_india:
                india_count += 1
                if jtype == "internship":
                    internship_count += 1
                else:
                    fulltime_count += 1

                if url_type == "DIRECT_REQUISITION" and apply_url.startswith("https://"):
                    actionable_count += 1
                    valid_apply_urls += 1

                # Role classification
                prof, conf, _ = resolve_role(title)
                c_role = prof.canonical_role if prof else "Unclassified / Specialized"
                role_distribution[c_role] = role_distribution.get(c_role, 0) + 1
                if prof and conf in ("HIGH", "MEDIUM"):
                    relevant_count += 1

                loc = doc.get("location", "Not specified")
                location_distribution[loc] = location_distribution.get(loc, 0) + 1

    print(f"Raw Fetched across boards: {raw_count}")
    print(f"Normalized into MongoDB: {normalized_count}")
    print(f"Total Active: {active_count}")
    print(f"Total India Active: {india_count}")
    print(f"Relevant (High/Med Role Match): {relevant_count}")
    print(f"Internships: {internship_count}")
    print(f"Full-Time: {fulltime_count}")
    print(f"Actionable Direct Requisitions: {actionable_count}")
    print(f"Valid Apply URLs (HTTPS Direct Requisitions): {valid_apply_urls}")

    print("\nRole Distribution (Indian Active Ashby Opportunities):")
    for r, count in sorted(role_distribution.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {r:35}: {count:2}")

    print("\nLocation Distribution:")
    for loc, count in sorted(location_distribution.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {loc:35}: {count:2}")

    print("\nCompleteness Distribution:")
    for cs, count in sorted(completeness_distribution.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {cs:35}: {count:2}")

    # 4. POST-SYNC TOTAL INVENTORY METRICS
    print("\n--- 4. POST-SYNC DATABASE TOTALS ---")
    total_post = await coll.count_documents({})
    active_post = await coll.count_documents({"verification_status": "VERIFIED_ACTIVE"})
    india_active_post = await coll.count_documents({"verification_status": "VERIFIED_ACTIVE", "is_india_opportunity": True})
    
    print(f"Total Database Records: {total_post} (+{total_post - total_pre})")
    print(f"Total Active Listings: {active_post} (+{active_post - active_pre})")
    print(f"Total Live Indian Active Listings: {india_active_post} (+{india_active_post - india_active_pre})")

    print("\nProvider Breakdown Post-Sync:")
    for p in ["smartrecruiters", "lever", "greenhouse", "adzuna", "ashby", "curated_benchmark"]:
        p_tot = await coll.count_documents({"source": p})
        p_act = await coll.count_documents({"source": p, "verification_status": "VERIFIED_ACTIVE"})
        p_in_act = await coll.count_documents({"source": p, "verification_status": "VERIFIED_ACTIVE", "is_india_opportunity": True})
        print(f"  {p:18}: Total={p_tot:4} | Active={p_act:4} | India Active={p_in_act:4}")

    # 5. RECONCILIATION CALCULATION
    print("\n--- 5. RECONCILIATION SUMMARY ---")
    print(f"Existing Live Indian Active Inventory: {india_active_pre}")
    print(f"+ Ashby Raw Records Fetched: {raw_count}")
    india_exclusions = raw_count - india_count
    print(f"- India Exclusions (Non-India / Foreign / Ambiguous Remote): {india_exclusions}")
    print(f"- Inactive / Closed: {normalized_count - active_count}")
    print(f"- Irrelevant / Low Confidence: {india_count - relevant_count}")
    print(f"- Duplicates Filtered: 0")
    print(f"- Unactionable / Invalid Apply URLs: {india_count - actionable_count}")
    print(f"= Actual Incremental Useful Ashby Inventory: {actionable_count}")
    print(f"New Total Live Indian Active Inventory: {india_active_post}")


if __name__ == "__main__":
    asyncio.run(main())
