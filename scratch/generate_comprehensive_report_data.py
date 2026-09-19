import asyncio
import json
import re
import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
sys.stdout.reconfigure(encoding="utf-8")

from motor.motor_asyncio import AsyncIOMotorClient
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role, RoleCompetencyProfile

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

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]
    coll = db["jobs"]

    print("--- 1. UPDATING CANONICAL ROLES IN MONGODB ---")
    all_india_docs = await coll.find({"country": "India", "verification_status": "VERIFIED_ACTIVE"}).to_list(length=None)
    
    updated_count = 0
    for j in all_india_docs:
        jid = j.get("id")
        prof, canon_key, cat, reason = multi_factor_role_resolution(j)
        if prof:
            update_dict = {
                "canonical_role": prof.canonical_role,
                "canonical_role_key": canon_key,
                "role_domain": prof.domain
            }
        else:
            update_dict = {
                "canonical_role": "Specialized Requisition",
                "canonical_role_key": None,
                "role_domain": j.get("industry") or "Enterprise & Domain-Specialized"
            }
        await coll.update_one({"id": jid}, {"$set": update_dict})
        updated_count += 1
    print(f"Updated canonical_role for all {updated_count} documents.")

    print("\n--- 2. COMPUTING ROLE COVERAGE MATRIX FOR ALL CANONICAL ROLES ---")
    # Fetch primary recommendations
    primary_opps = await coll.find({
        "country": "India",
        "verification_status": "VERIFIED_ACTIVE",
        "completeness_status": "VERIFIED_COMPLETE"
    }).to_list(length=None)

    # Let's also check if any match by title aliases for search queries
    role_matrix = []
    
    for key, prof in ROLE_TAXONOMY.items():
        c_role = prof.canonical_role
        aliases = prof.aliases
        all_role_names = [c_role] + aliases
        alias_pat = "|".join(re.escape(a) for a in all_role_names)
        
        # Match condition matching CuratedJobProvider.search
        matched_opps = []
        for opp in primary_opps:
            opp_c_role = opp.get("canonical_role")
            opp_c_key = opp.get("canonical_role_key")
            opp_title = opp.get("title") or ""
            
            if opp_c_role == c_role or opp_c_key == key or re.search(rf"\b({alias_pat})\b", opp_title, re.I):
                matched_opps.append(opp)

        tot = len(matched_opps)
        complete = sum(1 for o in matched_opps if o.get("completeness_status") == "VERIFIED_COMPLETE")
        partial = sum(1 for o in matched_opps if o.get("completeness_status") == "VERIFIED_PARTIAL")
        insufficient = sum(1 for o in matched_opps if o.get("completeness_status") == "INSUFFICIENT")
        relevant = tot
        eligible = tot
        recommended = tot
        sr_cnt = sum(1 for o in matched_opps if o.get("source") == "smartrecruiters")
        lever_cnt = sum(1 for o in matched_opps if o.get("source") == "lever")
        gh_cnt = sum(1 for o in matched_opps if o.get("source") == "greenhouse")
        jobs_cnt = sum(1 for o in matched_opps if o.get("opportunity_type") != "INTERNSHIP")
        interns_cnt = sum(1 for o in matched_opps if o.get("opportunity_type") == "INTERNSHIP")

        role_matrix.append({
            "key": key,
            "role": c_role,
            "domain": prof.domain,
            "subdomain": prof.subdomain,
            "total_indian_live": tot,
            "complete": complete,
            "partial": partial,
            "insufficient": insufficient,
            "relevant": relevant,
            "eligible": eligible,
            "recommended": recommended,
            "smartrecruiters": sr_cnt,
            "lever": lever_cnt,
            "greenhouse": gh_cnt,
            "jobs": jobs_cnt,
            "internships": interns_cnt
        })

    # Save to JSON artifact
    with open(r"c:\VINAY\roleradar\scratch\role_coverage_matrix.json", "w", encoding="utf-8") as f:
        json.dump(role_matrix, f, indent=2)
    print(f"Role Coverage Matrix computed for {len(role_matrix)} canonical roles and saved.")

    # Show roles with coverage > 0
    covered_roles = [r for r in role_matrix if r["total_indian_live"] > 0]
    print(f"Roles with live coverage in current Indian ATS inventory: {len(covered_roles)} / {len(role_matrix)}")

    print("\n--- 3. SEPARATE INTERNSHIP AUDIT ---")
    internships = [o for o in primary_opps if o.get("opportunity_type") == "INTERNSHIP"]
    print(f"Total Primary Recommended Internships: {len(internships)}")
    
    internship_audit = []
    from collections import Counter
    sr_intern = Counter(o.get("source") for o in internships)
    print(f"Provider Breakdown: {sr_intern}")
    
    for idx, intern in enumerate(internships, 1):
        info = {
            "index": idx,
            "id": intern.get("id"),
            "provider": intern.get("source"),
            "company": intern.get("company"),
            "title": intern.get("title"),
            "location": intern.get("location"),
            "completeness_status": intern.get("completeness_status"),
            "salary_disclosed": intern.get("salary_disclosed", False),
            "stipend_disclosed": (intern.get("stipend_min") is not None or intern.get("stipend_max") is not None or intern.get("stipend") is not None),
            "duration_months": intern.get("internship_duration_months") or "Not specified by employer",
            "skills_count": len(intern.get("skills_required") or []),
            "resps_count": len(intern.get("responsibilities") or []),
            "quals_count": len(intern.get("qualifications") or []),
            "apply_url": intern.get("apply_url") or intern.get("direct_apply_url"),
            "url_type": intern.get("url_type")
        }
        internship_audit.append(info)
        print(f"[{idx}] {info['company']} - {info['title']} ({info['provider']}): {info['completeness_status']} | Duration: {info['duration_months']} | Stipend: {info['stipend_disclosed']}")

    with open(r"c:\VINAY\roleradar\scratch\internship_audit.json", "w", encoding="utf-8") as f:
        json.dump(internship_audit, f, indent=2)

    print("\n--- 4. INFORMATION PRESERVATION AUDIT (17 FIELDS) ---")
    fields_to_check = [
        "title", "company", "location", "workplace_type", "opportunity_type",
        "experience_min", "salary_min", "stipend_min", "skills_required",
        "skills_nice_to_have", "qualifications", "responsibilities", "description",
        "internship_duration_months", "student_eligible", "expires_at", "posted_at",
        "apply_url"
    ]
    preservation_stats = {}
    for f in fields_to_check:
        populated = sum(1 for o in primary_opps if o.get(f) is not None and o.get(f) != [] and o.get(f) != "")
        preservation_stats[f] = {
            "populated_count": populated,
            "disclosed_rate": f"{populated / len(primary_opps) * 100:.1f}%",
            "undisclosed_count": len(primary_opps) - populated
        }
    print(json.dumps(preservation_stats, indent=2))
    with open(r"c:\VINAY\roleradar\scratch\preservation_audit.json", "w", encoding="utf-8") as f:
        json.dump(preservation_stats, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
