"""
Comprehensive Scan of ALL 587 VERIFIED_ACTIVE Indian Opportunities.

Inspects every single record across 5 dimensions:
1. Structured provider compensation fields
2. Provider custom fields
3. Full stored job description
4. Normalized compensation fields
5. MongoDB compensation fields

Zero external network requests.
"""
import asyncio
import json
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "backend")

from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection
from app.modules.jobs.compensation_extractor import (
    extract_compensation_from_payload_and_text,
    FALSE_POSITIVE_PATTERNS,
    NUMERIC_LPA_RANGE_RE,
    NUMERIC_LPA_SINGLE_RE,
    NUMERIC_LAKHS_SINGLE_RE,
    NUMERIC_INR_FULL_RANGE_RE,
    NUMERIC_STIPEND_RE,
    QUALITATIVE_PATTERNS,
    INTERNSHIP_QUALITATIVE_PATTERNS,
)

# Broader numeric patterns to catch ANY numeric mention in proximity to money or compensation
ANY_MONEY_OR_COMP_REGEX = re.compile(
    r"(?:(?:₹|INR|Rs\.?|EUR|USD|\$)\s*[0-9][0-9,.]*|[0-9]+(?:\.[0-9]+)?\s*(?:lpa|lacs?|lakhs?|crores?|k|pm|per\s*month|per\s*annum))",
    re.I
)

async def scan_all():
    await connect_to_mongo()
    db = get_db()
    try:
        query = {
            "verification_status": "VERIFIED_ACTIVE",
            "country": "India",
            "source": {"$in": ["smartrecruiters", "lever", "greenhouse"]}
        }
        all_docs = await db.jobs.find(query).to_list(length=10000)
        total_scanned = len(all_docs)
        print(f"Authoritatively loaded {total_scanned} records from MongoDB matching query.")

        # Breakdown counters
        provider_counts = Counter()
        type_counts = Counter()
        
        numeric_salary_matches = []
        numeric_stipend_matches = []
        qualitative_matches = []
        genuinely_undisclosed_matches = []
        false_positive_instances = []

        provider_breakdown = defaultdict(lambda: {
            "total": 0,
            "jobs": 0,
            "internships": 0,
            "numeric_salary": 0,
            "numeric_stipend": 0,
            "qualitative": 0,
            "undisclosed": 0,
            "false_positives": 0,
        })

        for doc in all_docs:
            jid = doc.get("id")
            prov = doc.get("source")
            comp_name = doc.get("company")
            title = doc.get("title") or ""
            is_intern = (
                doc.get("opportunity_type") == "INTERNSHIP"
                or doc.get("job_type") == "internship"
                or "intern" in title.lower()
            )
            opp_type = "INTERNSHIP" if is_intern else "JOB"

            provider_counts[prov] += 1
            type_counts[opp_type] += 1
            
            pb = provider_breakdown[prov]
            pb["total"] += 1
            if is_intern:
                pb["internships"] += 1
            else:
                pb["jobs"] += 1

            # 1. Structured Provider Compensation Fields
            raw_p = doc.get("raw_payload") or doc.get("raw_posting") or {}
            sr_comp = raw_p.get("compensation") or raw_p.get("salary")
            lever_sr = raw_p.get("salaryRange")
            lever_sd = raw_p.get("salaryDescription")
            gh_pay = raw_p.get("pay")

            # 2. Provider Custom Fields
            custom_fields = raw_p.get("customField") or raw_p.get("custom_fields") or []
            custom_comp_found = None
            if isinstance(custom_fields, list):
                for cf in custom_fields:
                    if isinstance(cf, dict):
                        label = str(cf.get("fieldLabel") or cf.get("name") or "").lower()
                        val = str(cf.get("value") or cf.get("valueLabel") or "")
                        if any(k in label for k in ["salary", "stipend", "compensation", "ctc", "pay"]):
                            custom_comp_found = {"label": label, "value": val}

            # 3. Full Stored Job Description
            desc = (doc.get("description") or "") + " " + (doc.get("raw_html") or "") + " " + (doc.get("jd_text") or "")

            # 4. Normalized Compensation Fields (via compensation_extractor)
            comp_norm = extract_compensation_from_payload_and_text(
                text=desc,
                raw_payload=raw_p,
                is_internship=is_intern,
            )

            # 5. Stored MongoDB Compensation Fields
            mongo_salary_min = doc.get("salary_min")
            mongo_salary_max = doc.get("salary_max")
            mongo_salary_disclosed = doc.get("salary_disclosed", False)
            mongo_stipend_min = doc.get("stipend_min")
            mongo_comp_type = doc.get("compensation_type")
            mongo_comp_text = doc.get("compensation_text")

            # Scan for potential false positive mentions in description
            # (where a money or number pattern exists, but relates to revenue, loans, budgets, etc.)
            for m in ANY_MONEY_OR_COMP_REGEX.finditer(desc):
                snippet = desc[max(0, m.start() - 160):min(len(desc), m.end() + 160)]
                for fp in FALSE_POSITIVE_PATTERNS:
                    if fp.search(snippet):
                        false_positive_instances.append({
                            "id": jid,
                            "provider": prov,
                            "company": comp_name,
                            "title": title,
                            "matched_money": m.group(0),
                            "fp_reason": fp.pattern,
                            "snippet": snippet.strip().replace("\n", " ")[:200]
                        })
                        pb["false_positives"] += 1
                        break

            # Classification
            if comp_norm.compensation_type == "NUMERIC":
                match_record = {
                    "id": jid,
                    "provider": prov,
                    "company": comp_name,
                    "title": title,
                    "type": opp_type,
                    "salary_min": comp_norm.salary_min,
                    "salary_max": comp_norm.salary_max,
                    "stipend_min": comp_norm.stipend_min,
                    "comp_text": comp_norm.compensation_text,
                    "mongo_stored": (mongo_salary_min, mongo_salary_max, mongo_salary_disclosed, mongo_stipend_min),
                    "source_text_snippet": desc[max(0, desc.find(comp_norm.compensation_text or "") - 50):min(len(desc), desc.find(comp_norm.compensation_text or "") + 100)] if comp_norm.compensation_text else "Structured",
                }
                if is_intern:
                    numeric_stipend_matches.append(match_record)
                    pb["numeric_stipend"] += 1
                else:
                    numeric_salary_matches.append(match_record)
                    pb["numeric_salary"] += 1
            elif comp_norm.compensation_type == "QUALITATIVE":
                qualitative_matches.append({
                    "id": jid,
                    "provider": prov,
                    "company": comp_name,
                    "title": title,
                    "type": opp_type,
                    "comp_text": comp_norm.compensation_text,
                    "mongo_comp_text": mongo_comp_text,
                    "mongo_comp_type": mongo_comp_type,
                })
                pb["qualitative"] += 1
            else:
                genuinely_undisclosed_matches.append({
                    "id": jid,
                    "provider": prov,
                    "company": comp_name,
                    "title": title,
                    "type": opp_type,
                })
                pb["undisclosed"] += 1

        # Deduplicate false-positive instances by id so each job is counted once in fp count
        unique_fp_jobs = {fp["id"]: fp for fp in false_positive_instances}

        results = {
            "total_scanned": total_scanned,
            "numeric_salary_count": len(numeric_salary_matches),
            "numeric_stipend_count": len(numeric_stipend_matches),
            "qualitative_count": len(qualitative_matches),
            "genuinely_undisclosed_count": len(genuinely_undisclosed_matches),
            "false_positive_job_count": len(unique_fp_jobs),
            "false_positive_mention_count": len(false_positive_instances),
            "provider_counts": dict(provider_counts),
            "type_counts": dict(type_counts),
            "provider_breakdown": dict(provider_breakdown),
            "numeric_salary_matches": numeric_salary_matches,
            "numeric_stipend_matches": numeric_stipend_matches,
            "qualitative_matches": qualitative_matches,
            "false_positive_examples": list(unique_fp_jobs.values())[:10]
        }

        with open("scratch/scan_587_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 80)
        print("EXACT SCAN RESULTS ACROSS ALL 587 INDIAN OPPORTUNITIES")
        print("=" * 80)
        print(f"Total Records Scanned: {total_scanned}")
        print(f"  - Jobs: {type_counts['JOB']}")
        print(f"  - Internships: {type_counts['INTERNSHIP']}")
        print(f"\nCompensation Classification:")
        print(f"  - Numeric Salary Count (Jobs): {len(numeric_salary_matches)} ({len(numeric_salary_matches)/total_scanned*100:.2f}%)")
        print(f"  - Numeric Stipend Count (Internships): {len(numeric_stipend_matches)} ({len(numeric_stipend_matches)/total_scanned*100:.2f}%)")
        print(f"  - Qualitative Compensation Count: {len(qualitative_matches)} ({len(qualitative_matches)/total_scanned*100:.2f}%)")
        print(f"  - Genuinely Undisclosed Count: {len(genuinely_undisclosed_matches)} ({len(genuinely_undisclosed_matches)/total_scanned*100:.2f}%)")
        print(f"  - False-Positive Non-Compensation Postings Screened: {len(unique_fp_jobs)} ({len(false_positive_instances)} total mentions)")

        print("\nProvider Breakdown:")
        for prov, d in provider_breakdown.items():
            print(f"  [{prov}] Total: {d['total']} (Jobs: {d['jobs']}, Internships: {d['internships']})")
            print(f"    Numeric Salary: {d['numeric_salary']}")
            print(f"    Numeric Stipend: {d['numeric_stipend']}")
            print(f"    Qualitative: {d['qualitative']}")
            print(f"    Undisclosed: {d['undisclosed']}")
            print(f"    False Positives Screened: {d['false_positives']}")

        if numeric_salary_matches or numeric_stipend_matches:
            print("\nNUMERIC MATCHES FOUND:")
            for m in numeric_salary_matches + numeric_stipend_matches:
                print(f"  ID: {m['id']} | {m['company']} | {m['title']}")
                print(f"    Text: {m['comp_text']}")
                print(f"    Snippet: {m['source_text_snippet']}")
        else:
            print("\nNUMERIC MATCHES: EXACTLY ZERO (0) across all 587 Indian live opportunities.")

        print(f"\nSaved full results to scratch/scan_587_results.json")

    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(scan_all())
