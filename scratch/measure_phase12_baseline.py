import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    db = client["roleradar"]
    
    providers = ["smartrecruiters", "lever", "greenhouse", "adzuna", "curated_benchmark", "custom"]
    
    results = {}
    
    for p in providers:
        # All records for provider
        docs = await db["jobs"].find({"source": p}).to_list(10000)
        
        raw_count = len(docs)
        active_count = sum(1 for d in docs if d.get("verification_status") == "VERIFIED_ACTIVE" or d.get("is_active") is True)
        
        # India records: country == 'India' or location contains India
        from app.modules.jobs.location_normalization import is_india_opportunity
        india_docs = [d for d in docs if d.get("country") == "India" or is_india_opportunity(d.get("location", ""), d.get("description", ""))]
        india_count = len(india_docs)
        
        # Relevant records (India + active)
        india_active_docs = [d for d in india_docs if d.get("verification_status") == "VERIFIED_ACTIVE" or (p in ("smartrecruiters", "lever", "greenhouse") and d.get("is_active") is True)]
        
        # Internships vs Full-time within India records
        internships = sum(1 for d in india_docs if d.get("opportunity_type") == "INTERNSHIP" or d.get("job_type") == "internship" or "intern" in (d.get("title") or "").lower())
        full_time = india_count - internships
        
        # Valid Apply URLs vs Missing
        valid_apply = sum(1 for d in docs if bool((d.get("apply_url") or "").strip()) and d.get("apply_url", "").startswith(("http://", "https://")))
        missing_apply = raw_count - valid_apply
        
        # Quality metrics on India docs
        target_group = india_docs if india_docs else docs
        tg_count = max(len(target_group), 1)
        
        has_skills = sum(1 for d in target_group if len(d.get("required_skills", [])) > 0)
        has_exp = sum(1 for d in target_group if d.get("experience_required") is not None or d.get("min_experience_years") is not None or "years" in (d.get("description") or "").lower())
        has_qual = sum(1 for d in target_group if len(d.get("qualifications", [])) > 0 or "degree" in (d.get("description") or "").lower() or "b.tech" in (d.get("description") or "").lower())
        has_comp = sum(1 for d in target_group if d.get("compensation_type") not in (None, "UNDISCLOSED") or d.get("salary_disclosed") or d.get("stipend_min") is not None or d.get("salary_min") is not None)
        
        avg_desc_len = sum(len(d.get("description") or d.get("jd_text") or "") for d in target_group) / tg_count
        
        # Supported roles count
        distinct_roles = set(d.get("canonical_role") or d.get("title") for d in target_group if d.get("canonical_role") or d.get("title"))
        
        # Public feed count: only VERIFIED_ACTIVE and not benchmark or custom
        if p in ("curated_benchmark", "custom"):
            public_feed_count = 0
        elif p == "adzuna":
            public_feed_count = sum(1 for d in india_docs if d.get("verification_status") == "VERIFIED_ACTIVE")
        else:
            public_feed_count = sum(1 for d in india_docs if d.get("verification_status") == "VERIFIED_ACTIVE")

        results[p] = {
            "raw_count": raw_count,
            "active_count": active_count,
            "india_count": india_count,
            "relevant_count": len(india_active_docs),
            "internships": internships,
            "full_time": full_time,
            "valid_apply": valid_apply,
            "missing_apply": missing_apply,
            "skills_cov_pct": round((has_skills / tg_count) * 100, 1),
            "exp_cov_pct": round((has_exp / tg_count) * 100, 1),
            "qual_cov_pct": round((has_qual / tg_count) * 100, 1),
            "comp_cov_pct": round((has_comp / tg_count) * 100, 1),
            "avg_desc_len": round(avg_desc_len),
            "distinct_roles_count": len(distinct_roles),
            "public_feed_count": public_feed_count
        }

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "backend")
    asyncio.run(main())
