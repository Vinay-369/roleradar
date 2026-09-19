import asyncio
import re
import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
sys.stdout.reconfigure(encoding="utf-8")

from motor.motor_asyncio import AsyncIOMotorClient
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role, RoleCompetencyProfile

def clean_title_for_resolution(raw_title: str) -> list[str]:
    """Generates normalized title candidates from ATS title strings."""
    candidates = [raw_title]
    t = raw_title.strip()
    
    # Strip common enterprise internal project/grade codes: e.g. _L91, _MPIN, _ECT, _COB, _Ban, _NaP/TEF12, etc.
    t_clean = re.sub(r"_[A-Za-z0-9\/\-]+$", "", t)
    t_clean = re.sub(r"^IN_[A-Za-z0-9_]+_", "", t_clean)
    t_clean = re.sub(r"\b(?:Bengaluru|Bangalore|Mumbai|Delhi|Gurgaon|Gurugram|Pune|Noida|Hyderabad|Chennai|Coimbatore|Guwahati|India)\b", "", t_clean, flags=re.I)
    t_clean = re.sub(r"\b\d+\s*[-to–]+\s*\d+\s*(?:years?|yrs?)(?:\s+of\s+experience)?\b", "", t_clean, flags=re.I)
    t_clean = re.sub(r"\b\d+\+?\s*(?:years?|yrs?)(?:\s+of\s+experience)?\b", "", t_clean, flags=re.I)
    t_clean = re.sub(r"\s*-\s*flows\b", "", t_clean, flags=re.I)
    t_clean = re.sub(r"\s+", " ", t_clean).strip(" -_,()")
    
    if t_clean and t_clean != raw_title:
        candidates.append(t_clean)
        
    # Handle SDE specific variations:
    # "SDE III - Devops" -> "Devops Engineer"
    # "SDE IV - Data Engineer" -> "Data Engineer"
    # "SDE II - AI" -> "AI Engineer"
    # "Software Development Engineer III -Backend" -> "Backend Developer"
    # "Software Development Engineer III Data" -> "Data Engineer"
    # "Software Development Engineer III DevOps" -> "DevOps Engineer"
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

    # Handle QA / Tester variations
    if re.search(r"\b(?:automation\s+tester|automation\s+testing|selenium.*tester|test\s+engineer|qa\s+engineer)\b", t, re.I):
        candidates.append("QA / Test Engineer")
        
    # Handle Mobile Developer variations
    if re.search(r"\b(?:mobile\s+app.*developer|ios.*developer|android.*developer)\b", t, re.I):
        candidates.append("Mobile Developer")

    # Handle Firmware / Embedded variations
    if re.search(r"\b(?:firmware\s+engineer|embedded.*engineer|embedded.*developer)\b", t, re.I):
        candidates.append("Embedded Software Engineer")

    # Handle Product Manager variations
    if re.search(r"\b(?:group\s+product\s+manager|director\s*-\s*product|associate\s+product\s+manager|lead\s+product\s+manager)\b", t, re.I):
        candidates.append("Product Manager")

    # Handle Staff/Principal Observability/Infrastructure
    if re.search(r"\b(?:observability\s+platform|infrastructure\s+architect|cloud\s+operations)\b", t, re.I):
        if "observability" in t.lower():
            candidates.append("Site Reliability Engineer")
        elif "infrastructure" in t.lower():
            candidates.append("Infrastructure Engineer")
        elif "cloud" in t.lower():
            candidates.append("Cloud Engineer")

    return candidates

# Precompute profile matching cache
PROFILE_CACHE = [
    {
        "prof": prof,
        "core": [c.lower().strip() for c in prof.core_competencies if len(c.strip()) > 3],
        "tech_skills": {c.lower().strip() for c in prof.core_competencies} | {t.lower().strip() for t in prof.tools_technologies}
    }
    for prof in ROLE_TAXONOMY.values()
]

def multi_factor_role_resolution(job: dict) -> tuple[RoleCompetencyProfile | None, str, str]:
    """
    Multi-factor role resolution using:
    1. Direct title and ATS pattern cleanup
    2. Responsibilities and required skills inspection
    3. Technical domain matching
    4. Strict guard against non-tech/unrelated jobs being forced into canonical tech roles
    """
    raw_title = job.get("title") or ""
    
    # 1. Try cleaned title variants first
    for candidate_title in clean_title_for_resolution(raw_title):
        prof, conf, reason = resolve_role(candidate_title)
        if prof and conf in ("HIGH", "MEDIUM"):
            return prof, "TITLE_RESOLUTION", reason

    # Non-tech / enterprise operations exclusion keywords:
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
        return None, "SPECIALIZED_ENTERPRISE_ROLE", "EXPLICIT_NON_TECH_SPECIALIZATION"

    # 2. Inspect Skills & Responsibilities against Canonical Role Competencies
    skills = job.get("skills_required") or []
    resps = job.get("responsibilities") or []
    skills_set = {s.lower().strip() for s in skills}
    combined_text = " ".join([raw_title] + resps).lower()

    best_prof = None
    best_score = 0.0
    best_reason = ""

    for pdata in PROFILE_CACHE:
        prof = pdata["prof"]
        skill_overlap = len(skills_set.intersection(pdata["tech_skills"]))
        resp_matches = sum(1 for c in pdata["core"] if c in combined_text)

        total_evidence_score = (skill_overlap * 2.5) + (resp_matches * 1.0)
        
        # High evidence threshold required to assign canonical role
        if total_evidence_score >= 6.0 and total_evidence_score > best_score:
            best_score = total_evidence_score
            best_prof = prof
            best_reason = f"MULTI_FACTOR_EVIDENCE (skills={skill_overlap}, resps={resp_matches}, score={total_evidence_score:.1f})"

    if best_prof:
        return best_prof, "COMPETENCY_EVIDENCE", best_reason

    return None, "SPECIALIZED_REQUISITION", "UNCLASSIFIED_SPECIALIZED"


async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]
    primary_jobs = await db.jobs.find({
        "country": "India",
        "verification_status": "VERIFIED_ACTIVE",
        "completeness_status": "VERIFIED_COMPLETE"
    }).to_list(length=None)

    resolved_count = 0
    specialized_count = 0
    role_counts = {}
    resolution_reasons = {}

    for j in primary_jobs:
        prof, cat, reason = multi_factor_role_resolution(j)
        if prof:
            resolved_count += 1
            r_name = prof.canonical_role
            role_counts[r_name] = role_counts.get(r_name, 0) + 1
            resolution_reasons[cat] = resolution_reasons.get(cat, 0) + 1
        else:
            specialized_count += 1
            resolution_reasons[cat] = resolution_reasons.get(cat, 0) + 1

    print(f"Total Primary Opportunities: {len(primary_jobs)}")
    print(f"Resolved to Canonical Roles: {resolved_count}")
    print(f"Honestly Retained as Specialized / Unclassified: {specialized_count}")
    print(f"\nResolution Categories: {resolution_reasons}")
    print(f"\nTop 25 Canonical Roles by Opportunity Count:")
    sorted_roles = sorted(role_counts.items(), key=lambda x: x[1], reverse=True)[:25]
    for r, c in sorted_roles:
        print(f"  {r}: {c}")

if __name__ == "__main__":
    asyncio.run(main())
