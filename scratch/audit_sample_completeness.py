import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.services import get_canonical_job_requirements
from app.modules.jobs.routes import _strip_for_detail, _strip_for_list

async def trace_sample():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Sample jobs per provider
    samples = []
    for prov in ["smartrecruiters", "lever", "greenhouse"]:
        # Find up to 5 jobs with description
        cur = db[Collections.JOBS].find({
            "verification_status": "VERIFIED_ACTIVE",
            "country": "India",
            "source": prov,
            "job_type": "full_time"
        }).limit(5)
        samples.extend(await cur.to_list(5))

    # All internships
    cur_interns = db[Collections.JOBS].find({
        "verification_status": "VERIFIED_ACTIVE",
        "country": "India",
        "job_type": "internship"
    })
    intern_samples = await cur_interns.to_list(20)
    samples.extend(intern_samples)

    print(f"Total sampled opportunities: {len(samples)} (Jobs={len(samples)-len(intern_samples)}, Internships={len(intern_samples)})")

    audit_rows = []
    for doc in samples:
        # Trace fields
        # Run canonical resolver to see what gets extracted
        reqs = await get_canonical_job_requirements(db, doc)
        detail = _strip_for_detail(doc)

        row = {
            "id": doc.get("id"),
            "source": doc.get("source"),
            "type": doc.get("job_type"),
            "title": doc.get("title"),
            "company": doc.get("company"),
            "location": doc.get("location"),
            "has_raw": bool(doc.get("description") or doc.get("raw_html")),
            "stored_skills_req": len(doc.get("skills_required") or []),
            "canonical_skills_req": len(reqs.must_have_skills or reqs.required_skills or []),
            "stored_skills_pref": len(doc.get("skills_nice_to_have") or []),
            "canonical_skills_pref": len(reqs.preferred_skills or []),
            "stored_responsibilities": len(doc.get("responsibilities") or []),
            "canonical_responsibilities": len(reqs.responsibilities or []),
            "stored_qualifications": len(doc.get("qualifications") or []),
            "canonical_qualifications": len(reqs.qualifications or []),
            "stored_exp_min": doc.get("experience_min"),
            "canonical_exp_min": reqs.min_years_experience,
            "stored_salary": doc.get("salary_min"),
            "stored_stipend": doc.get("stipend_min") or doc.get("stipend"),
            "stored_comp_text": doc.get("compensation_text"),
            "apply_url": doc.get("apply_url"),
            "is_direct_apply": doc.get("is_direct_apply"),
        }
        audit_rows.append(row)

    print("\nSample Audit Matrix Summary:")
    for r in audit_rows[:10]:
        print(f"[{r['source'][:2].upper()}] {r['title'][:30]:30} | ReqSkills: st={r['stored_skills_req']} can={r['canonical_skills_req']} | Resp: st={r['stored_responsibilities']} can={r['canonical_responsibilities']} | Qual: st={r['stored_qualifications']} can={r['canonical_qualifications']} | Exp: st={r['stored_exp_min']} can={r['canonical_exp_min']} | Comp: {r['stored_comp_text'] or r['stored_salary']}")

    # Save complete audit rows
    with open("scratch/sample_completeness_matrix.json", "w") as f:
        json.dump(audit_rows, f, indent=2, default=str)
    print("\nSaved full matrix to scratch/sample_completeness_matrix.json")

if __name__ == "__main__":
    asyncio.run(trace_sample())
