import asyncio
import sys
import json
import time
sys.path.insert(0, "backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.providers import CuratedJobProvider
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role

async def generate_metrics():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    coll = db[Collections.JOBS]

    # Total documents
    total_docs = await coll.count_documents({})
    
    # Active Indian query
    active_cursor = coll.find({"verification_status": "VERIFIED_ACTIVE"})
    all_active = await active_cursor.to_list(length=10000)

    from app.modules.jobs.location_normalization import is_india_opportunity
    indian_active = [
        o for o in all_active
        if o.get("country") == "India" or is_india_opportunity(o.get("location", ""), o.get("description", ""))
    ]

    # Providers breakdown
    by_provider = {}
    by_quality = {}
    by_opp_type = {"FULL_TIME": 0, "INTERNSHIP": 0}
    by_completeness = {}

    numeric_salary_ids = []
    numeric_stipend_ids = []
    qualitative_comp_ids = []
    undisclosed_comp_count = 0

    has_skills_count = 0
    has_quals_count = 0
    has_resps_count = 0
    has_exp_count = 0

    direct_apply_count = 0
    unique_keys = set()
    duplicates_count = 0

    role_coverage = {k: {"jobs": 0, "internships": 0} for k in ROLE_TAXONOMY.keys()}
    other_roles = {}

    for o in indian_active:
        prov = o.get("source", "unknown")
        by_provider[prov] = by_provider.get(prov, 0) + 1

        comp_status = o.get("completeness_status", "UNKNOWN")
        by_completeness[comp_status] = by_completeness.get(comp_status, 0) + 1

        rec_qual = o.get("recommendation_quality", "UNKNOWN")
        by_quality[rec_qual] = by_quality.get(rec_qual, 0) + 1

        o_type = o.get("opportunity_type", "FULL_TIME")
        if o_type not in by_opp_type:
            by_opp_type[o_type] = 0
        by_opp_type[o_type] += 1

        # Direct apply
        if o.get("is_direct_apply"):
            direct_apply_count += 1

        # Deduplication check
        norm_title = (o.get("title") or "").strip().lower()
        norm_comp = (o.get("company") or "").strip().lower()
        norm_loc = (o.get("location") or "").strip().lower()
        key = (norm_comp, norm_title, norm_loc)
        if key in unique_keys:
            duplicates_count += 1
        else:
            unique_keys.add(key)

        # Compensation
        s_min = o.get("salary_min")
        s_max = o.get("salary_max")
        st_min = o.get("stipend_min")
        st_max = o.get("stipend_max")
        c_text = o.get("compensation_text")
        c_type = o.get("compensation_type")

        if (s_min and s_min > 0) or (s_max and s_max > 0):
            numeric_salary_ids.append((o["id"], o.get("salary_currency"), s_min, s_max))
        elif (st_min and st_min > 0) or (st_max and st_max > 0):
            numeric_stipend_ids.append((o["id"], st_min, st_max))
        elif c_type == "QUALITATIVE" or (c_text and not c_text.lower().startswith("compensation not")):
            qualitative_comp_ids.append(o["id"])
        else:
            undisclosed_comp_count += 1

        # Fields presence
        if o.get("skills_required"):
            has_skills_count += 1
        if o.get("qualifications"):
            has_quals_count += 1
        if o.get("responsibilities"):
            has_resps_count += 1
        if o.get("experience_min") is not None or o.get("experience_max") is not None:
            has_exp_count += 1

        # Role classification
        prof, _, _ = resolve_role(o.get("title", ""))
        if prof:
            canon_key = None
            for k, p in ROLE_TAXONOMY.items():
                if p.canonical_role == prof.canonical_role:
                    canon_key = k
                    break
            if canon_key and canon_key in role_coverage:
                if o_type == "INTERNSHIP":
                    role_coverage[canon_key]["internships"] += 1
                else:
                    role_coverage[canon_key]["jobs"] += 1
            else:
                other_roles[o.get("title")] = other_roles.get(o.get("title"), 0) + 1
        else:
            other_roles[o.get("title")] = other_roles.get(o.get("title"), 0) + 1

    # Query timing test for search API
    curated = CuratedJobProvider(db)
    t0 = time.perf_counter()
    jobs_res = await curated.search({"limit": 50, "skip": 0, "region": "india", "active_discovery_only": True})
    t_jobs = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    interns_res = await curated.search({"limit": 50, "skip": 0, "region": "india", "opportunity_type": "INTERNSHIP", "active_discovery_only": True})
    t_interns = (time.perf_counter() - t0) * 1000

    report = {
        "total_documents_in_db": total_docs,
        "total_active_indian": len(indian_active),
        "by_provider": by_provider,
        "by_completeness_status": by_completeness,
        "by_quality": by_quality,
        "by_opp_type": by_opp_type,
        "eligible_primary_recommendations": by_completeness.get("VERIFIED_COMPLETE", 0) + by_completeness.get("VERIFIED_PARTIAL", 0),
        "insufficient_count": by_completeness.get("INSUFFICIENT", 0),
        "direct_apply_count": direct_apply_count,
        "direct_apply_rate": round(direct_apply_count / len(indian_active) * 100, 2),
        "duplicate_count": duplicates_count,
        "duplicate_rate": round(duplicates_count / len(indian_active) * 100, 2),
        "compensation": {
            "numeric_salary_count": len(numeric_salary_ids),
            "numeric_stipend_count": len(numeric_stipend_ids),
            "qualitative_count": len(qualitative_comp_ids),
            "undisclosed_count": undisclosed_comp_count,
            "numeric_salary_samples": numeric_salary_ids,
        },
        "field_recovery": {
            "skills_extracted_count": has_skills_count,
            "qualifications_extracted_count": has_quals_count,
            "responsibilities_extracted_count": has_resps_count,
            "experience_extracted_count": has_exp_count,
        },
        "performance_latency_ms": {
            "jobs_search_p50": round(t_jobs, 2),
            "internships_search_p50": round(t_interns, 2),
            "jobs_returned_count": len(jobs_res),
            "internships_returned_count": len(interns_res),
        },
        "role_coverage": role_coverage,
        "unmatched_or_specialized_titles_count": sum(other_roles.values()),
    }

    print(json.dumps(report, indent=2))
    with open("scratch/final_report_data.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    asyncio.run(generate_metrics())
