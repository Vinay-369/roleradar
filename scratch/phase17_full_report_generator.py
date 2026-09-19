import asyncio
import json
import re
import sys
import time
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
sys.stdout.reconfigure(encoding="utf-8")

from motor.motor_asyncio import AsyncIOMotorClient
from collections import Counter, defaultdict
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role
from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location
from app.modules.jobs.url_classifier import classify_application_url, ApplicationUrlType
from app.modules.jobs.deduplication import compute_dedup_key

async def generate_all_tables():
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    db = client["roleradar"]
    coll = db["jobs"]

    all_docs = await coll.find({}).to_list(length=None)
    total_db_docs = len(all_docs)

    # 1. LIVE INDIAN ACTIVE OPPORTUNITIES DEFINITION
    # Live Indian active requisitions are:
    # source in [smartrecruiters, lever, greenhouse], country=India / location in India, verification_status=VERIFIED_ACTIVE
    
    live_active_india = []
    seen_dedup = set()
    duplicates_count = 0
    
    for d in all_docs:
        src = d.get("source")
        if src not in ["smartrecruiters", "lever", "greenhouse"]:
            continue
        c = (d.get("country") or "").strip()
        loc = (d.get("location") or "").strip()
        is_ind = (c.lower() in ["india", "in"]) or is_india_opportunity(loc) or (extract_country_from_location(loc) == "India")
        if not is_ind:
            continue
        if d.get("verification_status") != "VERIFIED_ACTIVE":
            continue
            
        k = compute_dedup_key(d.get("company", ""), d.get("title", ""), d.get("location", ""), d.get("job_type", "full_time"), d.get("is_remote", False))
        if k in seen_dedup:
            duplicates_count += 1
        else:
            seen_dedup.add(k)
            live_active_india.append(d)

    print(f"Total Database Documents: {total_db_docs}")
    print(f"Total Unique Live Active Indian Opportunities: {len(live_active_india)}")

    # 2. ROLE COVERAGE TABLE (for all 119 canonical roles in taxonomy + Specialized Requisition)
    canonical_roles = sorted(list(set(v.canonical_role for v in ROLE_TAXONOMY.values())))
    
    role_metrics = {}
    for r in canonical_roles:
        role_metrics[r] = {
            "active_india": 0,
            "relevant": 0,
            "valid_apply": 0,
            "primary": 0,
            "secondary": 0,
            "rejected": 0
        }
    role_metrics["Specialized Requisition"] = {
        "active_india": 0,
        "relevant": 0,
        "valid_apply": 0,
        "primary": 0,
        "secondary": 0,
        "rejected": 0
    }

    # Also track internships per role
    intern_role_metrics = {r: {"active_india": 0, "relevant": 0, "primary": 0, "secondary": 0} for r in canonical_roles}
    intern_role_metrics["Specialized Requisition"] = {"active_india": 0, "relevant": 0, "primary": 0, "secondary": 0}

    # Evaluate docs against roles
    for d in live_active_india:
        crole = d.get("canonical_role") or "Specialized Requisition"
        if crole not in role_metrics:
            crole = "Specialized Requisition"

        desc = (d.get("description") or d.get("jd_text") or "").strip()
        is_relevant = len(desc) >= 50
        
        apply_url = (d.get("apply_url") or d.get("direct_apply_url") or "").strip()
        is_valid_apply = bool(apply_url and ("http://" in apply_url or "https://" in apply_url))

        # Check completeness / quality tier in doc
        qtier = d.get("quality_tier") or ("PRIMARY" if d.get("completeness_status") == "VERIFIED_COMPLETE" else "SECONDARY")
        if not is_relevant or not is_valid_apply:
            qtier = "REJECTED"

        role_metrics[crole]["active_india"] += 1
        if is_relevant:
            role_metrics[crole]["relevant"] += 1
        if is_valid_apply:
            role_metrics[crole]["valid_apply"] += 1
        
        if qtier == "PRIMARY":
            role_metrics[crole]["primary"] += 1
        elif qtier == "SECONDARY":
            role_metrics[crole]["secondary"] += 1
        else:
            role_metrics[crole]["rejected"] += 1

        # Check internship
        is_intern = (d.get("opportunity_type") == "INTERNSHIP")
        if is_intern:
            intern_role_metrics[crole]["active_india"] += 1
            if is_relevant:
                intern_role_metrics[crole]["relevant"] += 1
            if qtier == "PRIMARY":
                intern_role_metrics[crole]["primary"] += 1
            elif qtier == "SECONDARY":
                intern_role_metrics[crole]["secondary"] += 1

    # 3. INFORMATION COVERAGE TABLE
    # Fields: Salary, Stipend, Skills, Experience, Qualifications, Responsibilities, Apply URL
    info_cov = {
        "Salary": {"known": 0, "unknown": 0, "invalid": 0},
        "Stipend": {"known": 0, "unknown": 0, "invalid": 0},
        "Skills": {"known": 0, "unknown": 0, "invalid": 0},
        "Experience": {"known": 0, "unknown": 0, "invalid": 0},
        "Qualifications": {"known": 0, "unknown": 0, "invalid": 0},
        "Responsibilities": {"known": 0, "unknown": 0, "invalid": 0},
        "Apply URL": {"known": 0, "unknown": 0, "invalid": 0},
    }

    for d in live_active_india:
        # Salary
        sal = d.get("salary_range") or d.get("compensation") or d.get("salary_raw")
        if sal and str(sal).strip() and str(sal).strip().lower() not in ["none", "null", "undefined", "not specified", "unknown"]:
            info_cov["Salary"]["known"] += 1
        else:
            info_cov["Salary"]["unknown"] += 1

        # Stipend (relevant for internships)
        stip = d.get("stipend") or d.get("stipend_raw")
        if stip and str(stip).strip() and str(stip).strip().lower() not in ["none", "null", "undefined", "not specified", "unknown"]:
            info_cov["Stipend"]["known"] += 1
        else:
            info_cov["Stipend"]["unknown"] += 1

        # Skills
        sk = d.get("skills_required") or []
        if len(sk) > 0:
            info_cov["Skills"]["known"] += 1
        else:
            info_cov["Skills"]["unknown"] += 1

        # Experience
        exp_min = d.get("experience_min")
        exp_max = d.get("experience_max")
        if exp_min is not None or exp_max is not None:
            info_cov["Experience"]["known"] += 1
        else:
            info_cov["Experience"]["unknown"] += 1

        # Qualifications
        quals = d.get("qualifications") or []
        if len(quals) > 0:
            info_cov["Qualifications"]["known"] += 1
        else:
            info_cov["Qualifications"]["unknown"] += 1

        # Responsibilities
        resps = d.get("responsibilities") or []
        if len(resps) > 0:
            info_cov["Responsibilities"]["known"] += 1
        else:
            info_cov["Responsibilities"]["unknown"] += 1

        # Apply URL
        ap_url = (d.get("apply_url") or d.get("direct_apply_url") or "").strip()
        if ap_url and ("http://" in ap_url or "https://" in ap_url):
            info_cov["Apply URL"]["known"] += 1
        else:
            info_cov["Apply URL"]["invalid"] += 1

    # 4. PROVIDER QUALITY TABLE
    # Provider | Indian Inventory | Relevant | Direct Apply % | Duplicate % | Role Coverage | Internship Coverage
    # Let's collect raw per provider to get accurate dup %
    prov_quality = {}
    for prov in ["smartrecruiters", "lever", "greenhouse"]:
        p_raw = [d for d in all_docs if d.get("source") == prov]
        p_india_active = [d for d in live_active_india if d.get("source") == prov]
        p_rel = [d for d in p_india_active if len((d.get("description") or "").strip()) >= 50]
        p_direct_apply = [d for d in p_india_active if d.get("apply_url_type") == "DIRECT_APPLICATION_PAGE" or "smartrecruiters.com" in (d.get("apply_url") or "") or "lever.co" in (d.get("apply_url") or "") or "greenhouse.io" in (d.get("apply_url") or "")]
        
        # duplicates in raw
        p_keys = set()
        p_dups = 0
        for d in p_raw:
            k = compute_dedup_key(d.get("company", ""), d.get("title", ""), d.get("location", ""), d.get("job_type", "full_time"), d.get("is_remote", False))
            if k in p_keys:
                p_dups += 1
            else:
                p_keys.add(k)
        
        roles_covered = len(set(d.get("canonical_role") for d in p_india_active if d.get("canonical_role") and d.get("canonical_role") != "Specialized Requisition"))
        interns_count = sum(1 for d in p_india_active if d.get("opportunity_type") == "INTERNSHIP")

        prov_quality[prov] = {
            "indian_inventory": len(p_india_active),
            "relevant": len(p_rel),
            "direct_apply_pct": round(len(p_direct_apply) / len(p_india_active) * 100, 1) if p_india_active else 0.0,
            "duplicate_pct": round(p_dups / len(p_raw) * 100, 2) if p_raw else 0.0,
            "role_coverage": roles_covered,
            "internship_coverage": interns_count
        }

    # 5. REJECTION FUNNEL TABLE
    # Stage | Count | Percentage Lost
    # Raw Direct ATS: 2747
    # -> Normalized: 2747 (0% lost)
    # -> Deduplicated: 2745 (2 duplicates lost, 0.07%)
    # -> India Classified: 590 (2155 lost, 78.5%)
    # -> Active Requisitions: 588 (2 closed lost, 0.34%)
    # -> Relevant Requisitions: 587 (1 stub lost, 0.17%)
    # -> Valid Apply Requisitions: 587 (0 lost, 0.0%)
    # -> Recommended Tiers:
    #      Primary: 250 (42.6%)
    #      Secondary: 337 (57.4%)
    #      Rejected: 1 (0.17%)

    out_data = {
        "total_db_docs": total_db_docs,
        "unique_live_active_india": len(live_active_india),
        "role_metrics": role_metrics,
        "intern_role_metrics": intern_role_metrics,
        "info_coverage": info_cov,
        "provider_quality": prov_quality
    }

    with open(r"c:\VINAY\roleradar\scratch\phase17_full_report_metrics.json", "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print("Successfully generated all Phase 17 metrics in scratch/phase17_full_report_metrics.json")

if __name__ == "__main__":
    asyncio.run(generate_all_tables())
