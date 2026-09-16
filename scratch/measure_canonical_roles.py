import asyncio
import json
import sys
sys.path.insert(0, "backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role

CANONICAL_ROLES_TO_CHECK = [
    "Full Stack Developer", "Frontend Developer", "Backend Engineer", "Software Engineer",
    "Mobile Developer", "QA Engineer", "Data Analyst", "Data Engineer", "Data Scientist",
    "Machine Learning Engineer", "AI Engineer", "DevOps Engineer", "Cloud Architect",
    "Site Reliability Engineer", "Cybersecurity Analyst", "UI/UX Designer", "Product Manager",
    "Technical Recruiter", "Business Development Representative", "Digital Marketing Specialist",
    "Financial Analyst", "Operations Manager"
]

async def main():
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    db = client["roleradar"]
    
    # Fetch all active India jobs
    docs = await db["jobs"].find({
        "$or": [
            {"country": "India"},
            {"location": {"$regex": "India", "$options": "i"}}
        ]
    }).to_list(10000)
    
    # Resolve canonical role for each doc if not present
    for d in docs:
        if not d.get("canonical_role"):
            prof, _, _ = resolve_role(d.get("title", ""))
            if prof:
                d["canonical_role"] = prof.canonical_role
            else:
                d["canonical_role"] = d.get("title", "Unknown")
                
    # Also include any remaining roles in ROLE_TAXONOMY
    all_canon_roles = sorted(list(set(CANONICAL_ROLES_TO_CHECK + [p.canonical_role for p in ROLE_TAXONOMY.values()])))
    
    role_metrics = []
    
    for r in all_canon_roles:
        matching = [d for d in docs if (d.get("canonical_role") or "").lower() == r.lower() or r.lower() in (d.get("title") or "").lower()]
        
        ats_count = sum(1 for d in matching if d.get("source") in ("smartrecruiters", "lever", "greenhouse"))
        adzuna_count = sum(1 for d in matching if d.get("source") == "adzuna")
        
        internships = sum(1 for d in matching if d.get("opportunity_type") == "INTERNSHIP" or d.get("job_type") == "internship" or "intern" in (d.get("title") or "").lower())
        
        # Fresher/Entry vs Experienced
        fresher = sum(1 for d in matching if d.get("min_experience_years", 0) <= 1 or d.get("experience_required") in (None, "ENTRY", "0-1", "0-2") or "fresher" in (d.get("description") or "").lower() or "graduate" in (d.get("description") or "").lower() or internships > 0)
        experienced = len(matching) - fresher
        if experienced < 0:
            experienced = 0
            
        zero_res = "YES" if len(matching) == 0 else "NO"
        
        role_metrics.append({
            "canonical_role": r,
            "india_total": len(matching),
            "live_employer_ats": ats_count,
            "adzuna": adzuna_count,
            "internships": internships,
            "fresher": fresher,
            "experienced": experienced,
            "zero_result": zero_res
        })
        
    print(json.dumps(role_metrics, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
