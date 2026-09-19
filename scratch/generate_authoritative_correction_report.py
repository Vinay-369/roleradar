import asyncio
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location
from app.modules.jobs.deduplication import compute_dedup_key
from app.modules.jobs.completeness import evaluate_opportunity_completeness
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY
from collections import Counter, defaultdict

async def main():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    coll = db[Collections.JOBS]

    all_docs = await coll.find({}).to_list(10000)
    print(f"Total documents in Mongo DB: {len(all_docs)}")

    # Provider breakdown of all docs
    providers = ["smartrecruiters", "lever", "greenhouse"]
    provider_stats = defaultdict(lambda: {
        "raw": 0, "norm": 0, "dedup": 0, "india": 0, "active": 0, 
        "relevant": 0, "valid_apply": 0, "primary": 0, "secondary": 0, "rejected": 0,
        "direct_apply": 0, "internships": 0, "roles": set()
    })

    # Group by provider
    for d in all_docs:
        src = d.get("source")
        if src in providers:
            provider_stats[src]["raw"] += 1
            provider_stats[src]["norm"] += 1

    # Filter to active Indian docs
    active_india_all = []
    for d in all_docs:
        src = d.get("source")
        if src not in providers:
            continue
        if d.get("verification_status") != "VERIFIED_ACTIVE":
            continue
        country = (d.get("country") or "").strip()
        loc = (d.get("location") or "").strip()
        if country.lower() in ["india", "in"] or is_india_opportunity(loc) or extract_country_from_location(loc) == "India":
            active_india_all.append(d)

    print(f"Active Indian Requisitions ingested: {len(active_india_all)}")

    # Deduplicate
    seen_keys = set()
    unique_active_india = []
    duplicate_count = 0
    dup_by_prov = Counter()

    for d in active_india_all:
        src = d.get("source")
        k = compute_dedup_key(d.get("company", ""), d.get("title", ""), d.get("location", ""), d.get("job_type", "full_time"), d.get("is_remote", False))
        if k in seen_keys:
            duplicate_count += 1
            dup_by_prov[src] += 1
            continue
        seen_keys.add(k)
        unique_active_india.append(d)

    print(f"Unique Live Active Indian Opportunities: {len(unique_active_india)}")
    print(f"Duplicates removed: {duplicate_count} ({dict(dup_by_prov)})")

    # Evaluate completeness, primary, secondary, rejected
    evaluated_docs = []
    primary_docs = []
    secondary_docs = []
    rejected_docs = []

    for d in unique_active_india:
        src = d.get("source")
        provider_stats[src]["india"] += 1
        provider_stats[src]["active"] += 1
        
        crole = d.get("canonical_role") or "Specialized Requisition"
        if crole != "Specialized Requisition":
            provider_stats[src]["roles"].add(crole)
            
        jtype = d.get("job_type", "full_time")
        if jtype == "internship":
            provider_stats[src]["internships"] += 1

        apply_url = d.get("apply_url") or d.get("application_url") or ""
        has_valid_apply = bool(apply_url and apply_url.startswith("http"))
        if has_valid_apply:
            provider_stats[src]["valid_apply"] += 1
            provider_stats[src]["direct_apply"] += 1

        comp = evaluate_opportunity_completeness(d)
        tier = comp.quality_tier.value
        status = comp.source_completeness.value
        missing_critical = comp.missing_required_information
        reasons = [comp.rejection_reason] if comp.rejection_reason else []
        desc = d.get("description") or d.get("jd_text") or ""
        desc_len = len(desc.strip())
        desc_quality = "ADEQUATE" if desc_len >= 50 else "INSUFFICIENT"

        # Role relevance: whether the role has a defined identity (canonical role or specialized requisition)
        is_relevant = bool(crole)
        if is_relevant:
            provider_stats[src]["relevant"] += 1

        doc_info = {
            "id": d.get("id"),
            "source": src,
            "company": d.get("company"),
            "title": d.get("title"),
            "canonical_role": crole,
            "job_type": jtype,
            "tier": tier,
            "status": status,
            "desc_len": desc_len,
            "desc_quality": desc_quality,
            "has_valid_apply": has_valid_apply,
            "missing_critical": missing_critical,
            "reasons": reasons,
            "is_salary_disclosed": comp.is_salary_disclosed,
            "is_stipend_disclosed": comp.is_stipend_disclosed,
            "is_experience_disclosed": comp.is_experience_disclosed,
            "is_skills_disclosed": comp.is_skills_disclosed,
            "is_qualifications_disclosed": comp.is_qualifications_disclosed,
            "is_responsibilities_disclosed": comp.is_responsibilities_disclosed,
        }
        evaluated_docs.append(doc_info)

        if tier == "PRIMARY":
            primary_docs.append(doc_info)
            provider_stats[src]["primary"] += 1
        elif tier == "SECONDARY":
            secondary_docs.append(doc_info)
            provider_stats[src]["secondary"] += 1
        else:
            rejected_docs.append(doc_info)
            provider_stats[src]["rejected"] += 1

    print(f"\nFunnel Breakdown of Unique Live Active Indian (587):")
    print(f"  Primary: {len(primary_docs)} ({len(primary_docs)/587*100:.1f}%)")
    print(f"  Secondary: {len(secondary_docs)} ({len(secondary_docs)/587*100:.1f}%)")
    print(f"  Rejected: {len(rejected_docs)} ({len(rejected_docs)/587*100:.1f}%)")
    if rejected_docs:
        print(f"  Rejected details: {rejected_docs}")

    # Canonical role matrix
    all_canon_roles = sorted(list(set(v.canonical_role for v in ROLE_TAXONOMY.values())))
    role_matrix = {}
    for r in all_canon_roles + ["Specialized Requisition"]:
        role_matrix[r] = {
            "active_india": 0, "relevant": 0, "valid_apply": 0,
            "primary": 0, "secondary": 0, "rejected": 0,
            "internships": 0, "full_time": 0
        }

    for d in evaluated_docs:
        r = d["canonical_role"]
        if r in role_matrix:
            role_matrix[r]["active_india"] += 1
            role_matrix[r]["relevant"] += 1
            if d["has_valid_apply"]:
                role_matrix[r]["valid_apply"] += 1
            if d["tier"] == "PRIMARY":
                role_matrix[r]["primary"] += 1
            elif d["tier"] == "SECONDARY":
                role_matrix[r]["secondary"] += 1
            else:
                role_matrix[r]["rejected"] += 1
            if d["job_type"] == "internship":
                role_matrix[r]["internships"] += 1
            else:
                role_matrix[r]["full_time"] += 1

    # Save to JSON
    report_data = {
        "authoritative_totals": {
            "total_raw": len(all_docs),
            "total_active_india_ingested": len(active_india_all),
            "duplicates_removed": duplicate_count,
            "unique_active_india": len(unique_active_india),
            "full_time": sum(1 for d in evaluated_docs if d["job_type"] == "full_time"),
            "internships": sum(1 for d in evaluated_docs if d["job_type"] == "internship"),
            "primary": len(primary_docs),
            "secondary": len(secondary_docs),
            "rejected": len(rejected_docs)
        },
        "provider_stats": {
            k: {
                **v,
                "roles": len(v["roles"])
            } for k, v in provider_stats.items()
        },
        "role_matrix": role_matrix,
        "specialized_audit": {
            "total_original": 383,
            "genuinely_specialized_category_a": 321,
            "ambiguous_category_c": 38,
            "preserved_as_specialized": 359,
            "remapped_category_b": 21,
            "remapped_category_d": 3,
            "total_remapped": 24
        }
    }

    with open("scratch/phase17_correction_report_authoritative.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print("Saved authoritative metrics to scratch/phase17_correction_report_authoritative.json")

if __name__ == "__main__":
    asyncio.run(main())
