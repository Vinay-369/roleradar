import asyncio
import json
import re
import sys
from collections import defaultdict
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "backend")
sys.path.insert(0, ".")

from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection
from app.modules.jobs.schemas import JobOut
from app.modules.jobs.routes import _strip_for_detail
from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text
import httpx

async def run_audit():
    await connect_to_mongo()
    db = get_db()
    
    try:
        base_query = {
            "verification_status": "VERIFIED_ACTIVE",
            "country": "India",
            "source": {"$in": ["smartrecruiters", "lever", "greenhouse"]}
        }
        all_jobs = await db.jobs.find(base_query).to_list(length=10000)
        
        # Group by provider and opportunity type
        by_prov_type = defaultdict(lambda: {"jobs": [], "internships": []})
        for j in all_jobs:
            prov = j["source"]
            is_intern = (
                j.get("opportunity_type") == "INTERNSHIP"
                or j.get("job_type") == "internship"
                or "intern" in (j.get("title") or "").lower()
            )
            if is_intern:
                by_prov_type[prov]["internships"].append(j)
            else:
                by_prov_type[prov]["jobs"].append(j)

        sample: list[dict] = []
        for prov in ["smartrecruiters", "lever", "greenhouse"]:
            pool_jobs = by_prov_type[prov]["jobs"]
            pool_interns = by_prov_type[prov]["internships"]
            
            def comp_keyword_score(doc):
                text = (doc.get("description") or "") + " " + (doc.get("raw_html") or "")
                score = 0
                c = extract_compensation_from_payload_and_text(text)
                if c.salary_disclosed:
                    score += 10
                if any(w in text.lower() for w in ["salary", "stipend", "compensation", "ctc", "package"]):
                    score += 1
                return score
            
            pool_jobs.sort(key=comp_keyword_score, reverse=True)
            target_job_count = 15 if prov in ["smartrecruiters", "lever"] else 20
            selected_jobs = pool_jobs[:target_job_count]
            sample.extend(selected_jobs)
            sample.extend(pool_interns)

        audit_rows = []
        
        async with httpx.AsyncClient(timeout=8.0) as client:
            for idx, job in enumerate(sample, 1):
                jid = job.get("id")
                prov = job.get("source")
                company = job.get("company")
                board = job.get("company_board")
                title = job.get("title")
                raw_id = job.get("source_job_id")
                apply_url = job.get("apply_url")
                is_intern = (
                    job.get("opportunity_type") == "INTERNSHIP"
                    or job.get("job_type") == "internship"
                    or "intern" in (job.get("title") or "").lower()
                )
                opp_type = "INTERNSHIP" if is_intern else "JOB"
                
                # 1. Probe official public API payload
                raw_api_comp = None
                has_usable_api_comp = False
                try:
                    if prov == "smartrecruiters":
                        url = f"https://api.smartrecruiters.com/v1/companies/{board}/postings/{raw_id}"
                        r = await client.get(url)
                        if r.status_code == 200:
                            d = r.json()
                            raw_api_comp = d.get("compensation") or d.get("salary")
                            custom = d.get("customField") or []
                            for cf in custom:
                                label = str(cf.get("fieldLabel") or "").lower()
                                if any(w in label for w in ["salary", "compensation", "stipend", "pay", "ctc"]):
                                    raw_api_comp = cf
                                    has_usable_api_comp = True
                    elif prov == "lever":
                        url = f"https://api.lever.co/v0/postings/{board}/{raw_id}"
                        r = await client.get(url)
                        if r.status_code == 200:
                            d = r.json()
                            s_range = d.get("salaryRange")
                            s_desc = d.get("salaryDescription")
                            if s_range:
                                raw_api_comp = s_range
                                if s_range.get("min", 0) > 0 or s_range.get("max", 0) > 0:
                                    has_usable_api_comp = True
                            elif s_desc:
                                raw_api_comp = s_desc
                                has_usable_api_comp = True
                    elif prov == "greenhouse":
                        url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{raw_id}"
                        r = await client.get(url)
                        if r.status_code == 200:
                            d = r.json()
                            raw_api_comp = d.get("pay") or d.get("compensation")
                            if raw_api_comp:
                                has_usable_api_comp = True
                except Exception as e:
                    raw_api_comp = f"FetchError({e})"

                # 2. Check Description & Custom Fields in DB
                desc = (job.get("description") or "") + " " + (job.get("raw_html") or "")
                desc_comp = extract_compensation_from_payload_and_text(
                    text=desc,
                    raw_payload=None,
                    is_internship=is_intern,
                )
                numeric_desc_matches = [desc_comp.compensation_text] if (desc_comp.compensation_type == "NUMERIC" and desc_comp.compensation_text) else []
                qual_desc_matches = [desc_comp.compensation_text] if (desc_comp.compensation_type == "QUALITATIVE" and desc_comp.compensation_text) else []

                # 3. MongoDB & API state
                extracted_salary_min = job.get("salary_min")
                extracted_salary_max = job.get("salary_max")
                extracted_salary_disclosed = job.get("salary_disclosed", False)
                extracted_stipend_min = job.get("stipend_min")

                mongo_salary = (extracted_salary_min, extracted_salary_max, extracted_salary_disclosed, extracted_stipend_min)

                job_out = JobOut(**_strip_for_detail(job))
                api_salary = (job_out.salary_min, job_out.salary_max, job_out.salary_disclosed, job_out.stipend_min, job_out.compensation_type, job_out.compensation_text)

                # 4. UI Rendered Value
                if job_out.salary_disclosed and job_out.salary_min is not None:
                    if job_out.salary_max is not None and job_out.salary_max != job_out.salary_min:
                        ui_detail = f"₹{job_out.salary_min}–{job_out.salary_max} LPA"
                    else:
                        ui_detail = f"₹{job_out.salary_min} LPA"
                elif job_out.stipend_min is not None:
                    ui_detail = f"₹{job_out.stipend_min}/month"
                elif job_out.compensation_text:
                    ui_detail = job_out.compensation_text
                else:
                    ui_detail = "Compensation not disclosed by employer"

                if job_out.salary_min and job_out.salary_max:
                    ui_card = f"₹{job_out.salary_min}–{job_out.salary_max} LPA"
                elif job_out.salary_min:
                    ui_card = f"₹{job_out.salary_min}+ LPA"
                elif job_out.stipend_min:
                    ui_card = f"₹{job_out.stipend_min} / mo"
                elif job_out.compensation_text:
                    if "best in industry" in job_out.compensation_text.lower():
                        ui_card = "Best in industry"
                    elif "commensurate" in job_out.compensation_text.lower():
                        ui_card = "Commensurate"
                    else:
                        ui_card = "Competitive"
                elif is_intern:
                    ui_card = "Stipend not specified"
                else:
                    ui_card = "None (chip omitted)"

                # 5. Classification
                # RECOVERED | DROPPED | GENUINELY_UNDISCLOSED | PROVIDER_API_GAP
                if has_usable_api_comp:
                    if not job_out.salary_disclosed and job_out.salary_min is None:
                        classification = "DROPPED"
                        failure_layer = "provider_normalization"
                    else:
                        classification = "RECOVERED"
                        failure_layer = "None"
                elif desc_comp.salary_disclosed:
                    if desc_comp.compensation_type == "NUMERIC":
                        if job_out.salary_disclosed and (job_out.salary_min is not None or job_out.stipend_min is not None):
                            classification = "RECOVERED"
                            failure_layer = "None"
                        else:
                            classification = "DROPPED"
                            failure_layer = "extraction_parser"
                    else:  # QUALITATIVE
                        if job_out.compensation_text:
                            classification = "RECOVERED"
                            failure_layer = "None"
                        else:
                            classification = "DROPPED"
                            failure_layer = "extraction_parser / UI"
                else:
                    classification = "GENUINELY_UNDISCLOSED"
                    failure_layer = "None"

                row = {
                    "id": jid,
                    "provider": prov,
                    "company": company,
                    "title": title,
                    "type": opp_type,
                    "raw_api_comp": raw_api_comp,
                    "numeric_desc": numeric_desc_matches,
                    "qual_desc": list(dict.fromkeys(qual_desc_matches)),
                    "mongo": mongo_salary,
                    "api": api_salary,
                    "ui_detail": ui_detail,
                    "ui_card": ui_card,
                    "classification": classification,
                    "failure_layer": failure_layer,
                }
                audit_rows.append(row)

        total_sampled = len(audit_rows)
        recovered_count = sum(1 for r in audit_rows if r["classification"] == "RECOVERED")
        dropped_count = sum(1 for r in audit_rows if r["classification"] == "DROPPED")
        undisclosed_count = sum(1 for r in audit_rows if r["classification"] == "GENUINELY_UNDISCLOSED")
        api_gap_count = sum(1 for r in audit_rows if r["classification"] == "PROVIDER_API_GAP")
        
        num_salary_count = sum(1 for r in audit_rows if r["type"] == "JOB" and (r["numeric_desc"] or (r["raw_api_comp"] and isinstance(r["raw_api_comp"], dict) and r["raw_api_comp"].get("max", 0) > 0)))
        num_stipend_count = sum(1 for r in audit_rows if r["type"] == "INTERNSHIP" and (r["numeric_desc"] or (r["raw_api_comp"] and isinstance(r["raw_api_comp"], dict) and r["raw_api_comp"].get("max", 0) > 0)))
        qual_comp_count = sum(1 for r in audit_rows if r["qual_desc"] and not r["numeric_desc"])

        print("=" * 80)
        print("EXACT METRICS & STATISTICAL RATES (61 SAMPLED)")
        print("=" * 80)
        print(f"Total Sampled: {total_sampled}")
        print(f"  - Genuine Non-Disclosure: {undisclosed_count} ({undisclosed_count / total_sampled * 100:.2f}%)")
        print(f"  - Dropped Cases: {dropped_count} ({dropped_count / total_sampled * 100:.2f}%)")
        print(f"  - Recovered Cases: {recovered_count} ({recovered_count / total_sampled * 100:.2f}%)")
        print(f"  - Provider API Gaps: {api_gap_count} ({api_gap_count / total_sampled * 100:.2f}%)")
        print(f"\nDisclosure Rates:")
        job_total = sum(1 for r in audit_rows if r['type'] == 'JOB')
        intern_total = sum(1 for r in audit_rows if r['type'] == 'INTERNSHIP')
        print(f"  - Numeric Salary Disclosure Rate (Jobs): {num_salary_count} / {job_total} ({num_salary_count / job_total * 100:.2f}%)")
        print(f"  - Numeric Stipend Disclosure Rate (Internships): {num_stipend_count} / {intern_total} ({num_stipend_count / intern_total * 100:.2f}%)")
        recovery_pct = (recovered_count / (recovered_count + dropped_count) * 100) if (recovered_count + dropped_count) > 0 else 0.0
        print(f"  - Recovery Rate: {recovered_count} / {recovered_count + dropped_count} ({recovery_pct:.2f}%)")

        if dropped_count > 0:
            print("\nDROPPED CASES:")
            for r in audit_rows:
                if r["classification"] == "DROPPED":
                    print(f"  ID: {r['id']} | Prov: {r['provider']} | Company: {r['company']} | Title: {r['title']}")
                    print(f"    Numeric Desc: {r['numeric_desc']}")
                    print(f"    Qual Desc: {r['qual_desc']}")
                    print(f"    API Comp Text: {r.get('api')}")
                    print(f"    Failure Layer: {r['failure_layer']}")

        with open("scratch/forensic_salary_audit_results.json", "w", encoding="utf-8") as f:
            json.dump(audit_rows, f, indent=2, ensure_ascii=False)
        print("\nSaved results to scratch/forensic_salary_audit_results.json")

    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(run_audit())
