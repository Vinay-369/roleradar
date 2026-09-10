import asyncio
import json
import re
import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
sys.stdout.reconfigure(encoding="utf-8")

from motor.motor_asyncio import AsyncIOMotorClient
from collections import Counter, defaultdict
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role
from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location
from app.modules.jobs.url_classifier import classify_application_url, ApplicationUrlType
from app.modules.jobs.deduplication import compute_dedup_key

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]
    coll = db["jobs"]

    all_docs = await coll.find({}).to_list(length=None)
    print(f"Total documents in database: {len(all_docs)}")

    # Provider Inventory Audit
    providers = ["smartrecruiters", "lever", "greenhouse", "adzuna", "curated_benchmark", "custom"]
    
    # Machine-readable rejection reason tracker
    rejection_reasons = Counter()
    provider_metrics = {}
    
    for p in providers:
        p_docs = [d for d in all_docs if d.get("source") == p]
        raw_count = len(p_docs)
        
        # Normalization check: has valid title, company, and location
        normalized = [d for d in p_docs if (d.get("title") or "").strip() and (d.get("company") or "").strip()]
        
        # Deduplication check
        seen_keys = set()
        deduped = []
        dup_count = 0
        for d in normalized:
            k = compute_dedup_key(d.get("company", ""), d.get("title", ""), d.get("location", ""), d.get("job_type", "full_time"), d.get("is_remote", False))
            if k in seen_keys:
                dup_count += 1
                rejection_reasons[f"DUPLICATE_OPPORTUNITY ({p})"] += 1
            else:
                seen_keys.add(k)
                deduped.append(d)

        # India classification check
        india_docs = []
        for d in deduped:
            c = (d.get("country") or "").strip()
            loc = (d.get("location") or "").strip()
            is_ind = (c.lower() in ["india", "in"]) or is_india_opportunity(loc) or (extract_country_from_location(loc) == "India")
            if is_ind:
                india_docs.append(d)
            else:
                rejection_reasons[f"NON_INDIA_GEOGRAPHY ({p})"] += 1

        # Active / Verified check
        active_docs = []
        for d in india_docs:
            st = d.get("verification_status")
            if st == "VERIFIED_ACTIVE":
                active_docs.append(d)
            elif st == "CLOSED":
                rejection_reasons[f"CLOSED_REQUISITION ({p})"] += 1
            elif st == "MARKET_BENCHMARK":
                rejection_reasons[f"MARKET_BENCHMARK_NOT_LIVE ({p})"] += 1
            else:
                rejection_reasons[f"UNVERIFIED_STATUS_{st} ({p})"] += 1

        # Canonical role classified
        role_classified = []
        for d in active_docs:
            c_role = d.get("canonical_role")
            if c_role and c_role != "Specialized Requisition":
                role_classified.append(d)
            else:
                # Still relevant Indian requisition, but domain-specialized
                pass

        # Relevant: active India docs with meaningful scope (>= 50 chars description)
        relevant_docs = []
        for d in active_docs:
            desc = (d.get("description") or d.get("jd_text") or "").strip()
            if len(desc) >= 50:
                relevant_docs.append(d)
            else:
                rejection_reasons[f"INSUFFICIENT_DESCRIPTION ({p})"] += 1

        # Valid Apply: direct application URL
        valid_apply = []
        for d in relevant_docs:
            url = (d.get("apply_url") or d.get("direct_apply_url") or "").strip()
            if url and ("http://" in url or "https://" in url):
                valid_apply.append(d)
            else:
                rejection_reasons[f"INVALID_OR_MISSING_APPLY_URL ({p})"] += 1

        # Primary vs Secondary Recommendation Tiers
        # Primary: High confidence, richer employer info (resps or quals or skills >= 1 and desc >= 400)
        # Secondary: Legitimate, active, relevant, valid apply, but shorter description or unstructured sections
        primary = []
        secondary = []
        for d in valid_apply:
            resps = d.get("responsibilities") or []
            quals = d.get("qualifications") or []
            skills = d.get("skills_required") or []
            desc_len = len(d.get("description") or "")
            
            has_rich_employer_info = (len(resps) > 0 or len(quals) > 0 or len(skills) > 0) and desc_len >= 400
            if has_rich_employer_info:
                primary.append(d)
            else:
                secondary.append(d)

        # Split by Full-time, Internship, Fresher, Experienced
        ft = sum(1 for d in valid_apply if d.get("opportunity_type") != "INTERNSHIP")
        intern = sum(1 for d in valid_apply if d.get("opportunity_type") == "INTERNSHIP")
        fresher = sum(1 for d in valid_apply if d.get("fresher_friendly") or d.get("fresher_eligible") or (d.get("experience_min") is not None and d.get("experience_min") <= 1))
        experienced = sum(1 for d in valid_apply if d.get("experience_min") is not None and d.get("experience_min") > 1)
        unspecified_exp = len(valid_apply) - (fresher + experienced)

        provider_metrics[p] = {
            "raw": raw_count,
            "normalized": len(normalized),
            "duplicates": dup_count,
            "india": len(india_docs),
            "active": len(active_docs),
            "role_classified": len(role_classified),
            "relevant": len(relevant_docs),
            "valid_apply": len(valid_apply),
            "primary": len(primary),
            "secondary": len(secondary),
            "rejected": raw_count - len(valid_apply),
            "full_time": ft,
            "internship": intern,
            "fresher": fresher,
            "experienced": experienced,
            "unspecified_exp": unspecified_exp
        }

    print("\n========================================================")
    print("1. PROVIDER INVENTORY AUDIT TABLE")
    print("========================================================")
    print(f"{'Provider':<18} | {'Raw':<5} | {'Norm':<5} | {'Dup':<4} | {'India':<5} | {'Active':<6} | {'RoleCls':<7} | {'Relevant':<8} | {'ValidApp':<8} | {'Primary':<7} | {'Second':<6} | {'Rejected':<8}")
    print("-" * 115)
    for p, m in provider_metrics.items():
        print(f"{p:<18} | {m['raw']:<5} | {m['normalized']:<5} | {m['duplicates']:<4} | {m['india']:<5} | {m['active']:<6} | {m['role_classified']:<7} | {m['relevant']:<8} | {m['valid_apply']:<8} | {m['primary']:<7} | {m['secondary']:<6} | {m['rejected']:<8}")

    print("\n========================================================")
    print("2. EXPERIENCE & TYPE SPLIT (LIVE VALID INDIA REQUISITIONS)")
    print("========================================================")
    print(f"{'Provider':<18} | {'Full-Time':<9} | {'Internship':<10} | {'Fresher':<8} | {'Experienced':<11} | {'Unspec Exp':<10}")
    print("-" * 85)
    for p, m in provider_metrics.items():
        print(f"{p:<18} | {m['full_time']:<9} | {m['internship']:<10} | {m['fresher']:<8} | {m['experienced']:<11} | {m['unspecified_exp']:<10}")

    print("\n========================================================")
    print("3. MACHINE-READABLE REJECTION REASONS SUMMARY")
    print("========================================================")
    for reason, count in rejection_reasons.most_common():
        print(f"  {reason}: {count}")

    # Save to JSON
    with open(r"c:\VINAY\roleradar\scratch\phase17_audit_data.json", "w", encoding="utf-8") as f:
        json.dump({
            "provider_metrics": provider_metrics,
            "rejection_reasons": dict(rejection_reasons)
        }, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
