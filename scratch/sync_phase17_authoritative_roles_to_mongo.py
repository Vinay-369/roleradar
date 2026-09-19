import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location
from app.modules.jobs.deduplication import compute_dedup_key
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role, RoleCompetencyProfile
from collections import Counter
import re

def clean_title_for_resolution(raw_title: str) -> list[str]:
    candidates = [raw_title]
    t = raw_title.strip()
    
    t_clean = re.sub(r"_[A-Za-z0-9\/\-]+$", "", t)
    t_clean = re.sub(r"^IN_[A-Za-z0-9_]+_", "", t_clean)
    t_clean = re.sub(r"\b(?:Bengaluru|Bangalore|Mumbai|Delhi|Gurgaon|Gurugram|Pune|Noida|Hyderabad|Chennai|Coimbatore|Guwahati|India)\b", "", t_clean, flags=re.I)
    t_clean = re.sub(r"\b\d+\s*[-to–]+\s*\d+\s*(?:years?|yrs?)(?:\s+of\s+experience)?\b", "", t_clean, flags=re.I)
    t_clean = re.sub(r"\b\d+\+?\s*(?:years?|yrs?)(?:\s+of\s+experience)?\b", "", t_clean, flags=re.I)
    t_clean = re.sub(r"\s*-\s*flows\b", "", t_clean, flags=re.I)
    t_clean = re.sub(r"\s+", " ", t_clean).strip(" -_,()")
    
    if t_clean and t_clean != raw_title:
        candidates.append(t_clean)
        
    sde_match = re.search(r"\b(?:sde|software development engineer)\s*(?:[iIvVxX\d]+)?\s*[-–:]?\s*(?:backend|data engineer|devops|ai|gen\s*ai|salesforce\s*ai)?\b", t, re.I)
    if sde_match:
        sub_text = t.lower()
        if "backend" in sub_text:
            candidates.append("Backend Developer")
        elif "data" in sub_text:
            candidates.append("Data Engineer")
        elif "devops" in sub_text:
            candidates.append("DevOps Engineer")
        elif "ai" in sub_text or "machine learning" in sub_text:
            candidates.append("AI Engineer")
        elif re.search(r"\b(?:sde|software development engineer)\s*[iIvVxX\d]*\b", sub_text):
            candidates.append("Software Engineer")

    if re.search(r"\b(?:automation\s+tester|automation\s+testing|selenium.*tester|test\s+engineer|qa\s+engineer)\b", t, re.I):
        candidates.append("QA / Test Engineer")
        
    if re.search(r"\b(?:mobile\s+app.*developer|ios.*developer|android.*developer)\b", t, re.I):
        candidates.append("Mobile Developer")

    if re.search(r"\b(?:firmware\s+engineer|embedded.*engineer|embedded.*developer)\b", t, re.I):
        candidates.append("Embedded Software Engineer")

    if re.search(r"\b(?:group\s+product\s+manager|director\s*-\s*product|associate\s+product\s+manager|lead\s+product\s+manager)\b", t, re.I):
        candidates.append("Product Manager")

    if re.search(r"\b(?:observability\s+platform|infrastructure\s+architect|cloud\s+operations)\b", t, re.I):
        if "observability" in t.lower():
            candidates.append("Site Reliability Engineer")
        elif "infrastructure" in t.lower():
            candidates.append("Infrastructure Engineer")
        elif "cloud" in t.lower():
            candidates.append("Cloud Engineer")

    return candidates

PROFILE_CACHE = [
    {
        "prof": prof,
        "key": key,
        "core": [c.lower().strip() for c in prof.core_competencies if len(c.strip()) > 3],
        "tech_skills": {c.lower().strip() for c in prof.core_competencies} | {t.lower().strip() for t in prof.tools_technologies}
    }
    for key, prof in ROLE_TAXONOMY.items()
]

def multi_factor_role_resolution(job: dict) -> tuple[RoleCompetencyProfile | None, str | None, str, str]:
    raw_title = job.get("title") or ""
    
    for candidate_title in clean_title_for_resolution(raw_title):
        prof, conf, reason = resolve_role(candidate_title)
        if prof and conf in ("HIGH", "MEDIUM"):
            canon_key = None
            for key, p in ROLE_TAXONOMY.items():
                if p.canonical_role == prof.canonical_role:
                    canon_key = key
                    break
            return prof, canon_key, "TITLE_RESOLUTION", reason

    non_tech_markers = [
        "account executive", "sales", "procurement", "recruiting", "talent partner",
        "talent acquisition", "hr", "payroll", "finance", "taxation", "audit",
        "collections", "tele caller", "legal", "compliance", "real estate",
        "facilities", "reconciliation", "customer support", "cst", "community support",
        "voice over", "logistics", "manufacturing operations", "cluster head",
        "affiliate marketing", "media sales", "deal desk", "revenue operations"
    ]
    title_lower = raw_title.lower()
    if any(re.search(rf"\b{re.escape(m)}\b", title_lower) for m in non_tech_markers):
        return None, None, "SPECIALIZED_ENTERPRISE_ROLE", "EXPLICIT_NON_TECH_SPECIALIZATION"

    skills = job.get("skills_required") or []
    resps = job.get("responsibilities") or []
    skills_set = {s.lower().strip() for s in skills}
    combined_text = " ".join([raw_title] + resps).lower()

    best_prof = None
    best_key = None
    best_score = 0.0
    best_reason = ""

    for pdata in PROFILE_CACHE:
        prof = pdata["prof"]
        skill_overlap = len(skills_set.intersection(pdata["tech_skills"]))
        resp_matches = sum(1 for c in pdata["core"] if c in combined_text)

        total_evidence_score = (skill_overlap * 2.5) + (resp_matches * 1.0)
        
        if total_evidence_score >= 6.0 and total_evidence_score > best_score:
            best_score = total_evidence_score
            best_prof = prof
            best_key = pdata["key"]
            best_reason = f"MULTI_FACTOR_EVIDENCE (skills={skill_overlap}, resps={resp_matches}, score={total_evidence_score:.1f})"

    if best_prof:
        return best_prof, best_key, "COMPETENCY_EVIDENCE", best_reason

    return None, None, "SPECIALIZED_REQUISITION", "UNCLASSIFIED_SPECIALIZED"

async def sync():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    coll = db[Collections.JOBS]

    cursor = coll.find({"verification_status": "VERIFIED_ACTIVE"})
    all_active = await cursor.to_list(10000)
    
    in_docs = [
        o for o in all_active
        if o.get("country") == "India" or is_india_opportunity(o.get("location", ""), o.get("description", "")) or extract_country_from_location(o.get("location", "")) == "India"
    ]
    print(f"Total live active Indian docs in DB to sync: {len(in_docs)}")

    updated = 0
    for doc in in_docs:
        prof, canon_key, cat, reason = multi_factor_role_resolution(doc)
        if prof:
            new_role = prof.canonical_role
            new_key = canon_key
            new_domain = prof.domain
        else:
            new_role = "Specialized Requisition"
            new_key = "specialized_requisition"
            new_domain = doc.get("industry") or "Enterprise & Domain-Specialized"

        await coll.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "canonical_role": new_role,
                "canonical_role_key": new_key,
                "role_domain": new_domain
            }}
        )
        updated += 1

    print(f"Successfully synced {updated} Indian opportunities in MongoDB.")

if __name__ == "__main__":
    asyncio.run(sync())
