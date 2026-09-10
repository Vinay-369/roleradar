import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.location_normalization import is_india_opportunity
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role

async def run_audit():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # 1. Funnel calculation
    # Total in DB
    total_db = await db[Collections.JOBS].count_documents({})
    
    # Providers of interest
    providers = ["smartrecruiters", "lever", "greenhouse"]

    funnel_results = {}
    for prov in providers:
        p_total = await db[Collections.JOBS].count_documents({"source": prov})
        p_india = await db[Collections.JOBS].count_documents({"source": prov, "country": "India"})
        p_active = await db[Collections.JOBS].count_documents({"source": prov, "country": "India", "verification_status": "VERIFIED_ACTIVE"})
        p_direct = await db[Collections.JOBS].count_documents({"source": prov, "country": "India", "verification_status": "VERIFIED_ACTIVE", "url_type": "DIRECT_REQUISITION"})
        
        funnel_results[prov] = {
            "retrieved_in_db": p_total,
            "india_eligible": p_india,
            "verified_active": p_active,
            "direct_apply": p_direct
        }

    print("=== FUNNEL SUMMARY ===")
    for prov, stats in funnel_results.items():
        print(f"{prov}: {stats}")

    # 2. Inspect active Indian opportunities
    docs = await db[Collections.JOBS].find({
        "verification_status": "VERIFIED_ACTIVE",
        "country": "India",
        "source": {"$in": providers}
    }).to_list(1000)

    print(f"\nTotal Active Indian Opportunities Audited: {len(docs)}")

    # 3. Role coverage analysis across canonical roles
    canonical_roles = [prof.canonical_role for prof in ROLE_TAXONOMY.values()]
    role_coverage = {r: {"jobs": 0, "internships": 0, "total": 0} for r in canonical_roles}
    unclassified_count = 0

    for d in docs:
        title = d.get("title", "")
        prof, conf, method = resolve_role(title)
        is_intern = (
            d.get("job_type") == "internship"
            or d.get("opportunity_type") == "INTERNSHIP"
            or "intern" in title.lower()
        )
        if prof and prof.canonical_role in role_coverage:
            if is_intern:
                role_coverage[prof.canonical_role]["internships"] += 1
            else:
                role_coverage[prof.canonical_role]["jobs"] += 1
            role_coverage[prof.canonical_role]["total"] += 1
        else:
            unclassified_count += 1

    print("\n=== ROLE COVERAGE SUMMARY (Across 587 Indian live opportunities) ===")
    for r, counts in role_coverage.items():
        if counts["total"] > 0:
            print(f"  {r:32}: total={counts['total']:3d} (jobs={counts['jobs']:3d}, interns={counts['internships']:2d})")
    print(f"  Unclassified / Specialized Titles: {unclassified_count}")

if __name__ == "__main__":
    asyncio.run(run_audit())
