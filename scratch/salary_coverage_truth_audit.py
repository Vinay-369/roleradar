import asyncio
import json
import re
import sys
from collections import defaultdict
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection
import httpx

# Regex patterns for description analysis
NUMERIC_SALARY_PATTERNS = [
    re.compile(r"(?:₹|INR|Rs\.?)\s*[\d,]+(?:\s*[-–to]+\s*[\d,]+)?\s*(?:lpa|per\s*annum|p\.?a\.?|per\s*year|per\s*month|/month|pm)?", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?\s*[-–to]+\s*\d+(?:\.\d+)?\s*(?:lpa|lacs?|lakhs?)\b", re.IGNORECASE),
    re.compile(r"\b(?:ctc|salary|compensation|package|stipend)\s*[:\-]?\s*(?:₹|INR|Rs\.?)?\s*[\d,]+(?:\.\d+)?\s*(?:lpa|lacs?|lakhs?|k|pm|per\s*month)?\b", re.IGNORECASE),
    re.compile(r"\b\d+k\s*/\s*month\b", re.IGNORECASE),
]

NON_NUMERIC_COMPENSATION_PATTERNS = [
    re.compile(r"\b(?:competitive|best\s*in\s*industry|market\s*standard|attractive|industry\s*standard|commensurate\s*with\s*experience|as\s*per\s*market|great|decent)\s*(?:salary|compensation|package|stipend|pay|remuneration)\b", re.IGNORECASE),
    re.compile(r"\b(?:salary|compensation|remuneration)\s*(?:is\s*)?(?:negotiable|competitive|commensurate|not\s*a\s*constraint)\b", re.IGNORECASE),
]

async def audit():
    await connect_to_mongo()
    db = get_db()
    try:
        # 1. Authoritative Inventory Counts
        query = {
            "verification_status": "VERIFIED_ACTIVE",
            "country": "India",
            "source": {"$in": ["smartrecruiters", "lever", "greenhouse"]}
        }
        
        total_count = await db.jobs.count_documents(query)
        print("=" * 80)
        print("1. AUTHORITATIVE INVENTORY AUDIT")
        print("=" * 80)
        print(f"Total Indian VERIFIED_ACTIVE opportunities: {total_count}")
        
        provider_counts = {}
        for src in ["smartrecruiters", "lever", "greenhouse"]:
            c = await db.jobs.count_documents({**query, "source": src})
            provider_counts[src] = c
            print(f"  - {src}: {c}")
        
        # Check opportunity_type breakdown
        full_time_query = {**query, "opportunity_type": {"$ne": "INTERNSHIP"}}
        intern_query = {**query, "opportunity_type": "INTERNSHIP"}
        
        ft_count = await db.jobs.count_documents(full_time_query)
        intern_count = await db.jobs.count_documents(intern_query)
        print(f"\nOpportunity Type Breakdown:")
        print(f"  - Full-time / Direct Jobs: {ft_count}")
        print(f"  - Internships: {intern_count}")
        print(f"  - Total: {ft_count + intern_count}")
        
        # 2. Audit All Records in MongoDB
        cursor = db.jobs.find(query)
        records = await cursor.to_list(length=10000)
        
        print("\n" + "=" * 80)
        print("2. MONGO DB FIELD AUDIT (Checking what is stored in DB)")
        print("=" * 80)
        
        mongo_salary_min_count = sum(1 for r in records if r.get("salary_min") is not None and r.get("salary_min") > 0)
        mongo_salary_max_count = sum(1 for r in records if r.get("salary_max") is not None and r.get("salary_max") > 0)
        mongo_salary_disclosed_true = sum(1 for r in records if r.get("salary_disclosed") is True)
        mongo_stipend_count = sum(1 for r in records if r.get("stipend_min") is not None and r.get("stipend_min") > 0)
        
        print(f"Records with salary_min > 0: {mongo_salary_min_count}")
        print(f"Records with salary_max > 0: {mongo_salary_max_count}")
        print(f"Records with salary_disclosed == True: {mongo_salary_disclosed_true}")
        print(f"Records with stipend_min > 0: {mongo_stipend_count}")
        
        # 3. Description-Based Scanning for all 587 records
        print("\n" + "=" * 80)
        print("3. DESCRIPTION-BASED SALARY SCANNING (ALL RECORDS)")
        print("=" * 80)
        
        results_by_provider = defaultdict(lambda: {
            "total": 0,
            "numeric_salary_desc": [],
            "non_numeric_comp_desc": [],
            "unusable": [],
            "undisclosed": 0,
            "lost_in_roleradar": 0
        })
        
        for r in records:
            src = r.get("source")
            results_by_provider[src]["total"] += 1
            
            desc = (r.get("description") or "") + " " + (r.get("raw_html") or "")
            
            # Check for numeric salary in description
            has_numeric = False
            numeric_matches = []
            for pat in NUMERIC_SALARY_PATTERNS:
                m = pat.findall(desc)
                if m:
                    for match in m:
                        # Filter out false positives like "3+ to 7 yrs", "1-2 years experience"
                        if not re.search(r"yr|year|exp", match, re.I):
                            numeric_matches.append(match)
            
            if numeric_matches:
                has_numeric = True
                results_by_provider[src]["numeric_salary_desc"].append({
                    "id": r.get("id"),
                    "company": r.get("company"),
                    "title": r.get("title"),
                    "matches": numeric_matches[:3],
                    "desc_snippet": desc[:200]
                })
            
            if not has_numeric:
                # Check for non-numeric compensation
                non_num_matches = []
                for pat in NON_NUMERIC_COMPENSATION_PATTERNS:
                    m = pat.findall(desc)
                    if m:
                        non_num_matches.extend(m)
                
                if non_num_matches:
                    results_by_provider[src]["non_numeric_comp_desc"].append({
                        "id": r.get("id"),
                        "company": r.get("company"),
                        "title": r.get("title"),
                        "matches": non_num_matches[:3]
                    })
                else:
                    results_by_provider[src]["undisclosed"] += 1

        print("Description scan completed.")
        for src in ["smartrecruiters", "lever", "greenhouse"]:
            st = results_by_provider[src]
            print(f"\nProvider: {src} (Total: {st['total']})")
            print(f"  - Numeric Salary Matches in text: {len(st['numeric_salary_desc'])}")
            print(f"  - Non-numeric Compensation text: {len(st['non_numeric_comp_desc'])}")
            print(f"  - Undisclosed (no salary text): {st['undisclosed']}")
            if st["numeric_salary_desc"]:
                print(f"    Sample numeric matches: {st['numeric_salary_desc'][:2]}")
            if st["non_numeric_comp_desc"]:
                print(f"    Sample non-numeric matches: {st['non_numeric_comp_desc'][:2]}")

        # 4. Check Raw API Payloads for each Provider
        print("\n" + "=" * 80)
        print("4. SOURCE FIELD DISCOVERY (RAW ATS PAYLOAD AUDIT)")
        print("=" * 80)
        
        # We will fetch a live opening for each provider and inspect JSON fields!
        sample_jobs = {}
        for src in ["smartrecruiters", "lever", "greenhouse"]:
            for r in records:
                if r.get("source") == src:
                    sample_jobs[src] = r
                    break
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 4A: SmartRecruiters
            sr_job = sample_jobs.get("smartrecruiters")
            if sr_job:
                sr_id = sr_job.get("source_job_id")
                # e.g. company_board
                cb = sr_job.get("company_board") or sr_job.get("company")
                print(f"\n[SmartRecruiters Probe] ID: {sr_id}, Board: {cb}")
                url = f"https://api.smartrecruiters.com/v1/companies/{cb}/postings/{sr_id}"
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        print(f"  Keys in SR posting: {list(data.keys())}")
                        print(f"  compensation in SR?: {data.get('compensation')}")
                        print(f"  salary in SR?: {data.get('salary')}")
                        print(f"  customField in SR?: {data.get('customField')}")
                    else:
                        print(f"  SR fetch status: {resp.status_code}")
                except Exception as e:
                    print(f"  SR fetch error: {e}")

            # 4B: Lever
            lever_job = sample_jobs.get("lever")
            if lever_job:
                lever_id = lever_job.get("source_job_id")
                cb = lever_job.get("company_board")
                print(f"\n[Lever Probe] ID: {lever_id}, Board: {cb}")
                url = f"https://api.lever.co/v0/postings/{cb}/{lever_id}"
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        print(f"  Keys in Lever posting: {list(data.keys())}")
                        print(f"  salaryDescription in Lever?: {data.get('salaryDescription')}")
                        print(f"  salaryRange in Lever?: {data.get('salaryRange')}")
                        print(f"  categories in Lever?: {data.get('categories')}")
                    else:
                        print(f"  Lever fetch status: {resp.status_code}")
                except Exception as e:
                    print(f"  Lever fetch error: {e}")

            # 4C: Greenhouse
            gh_job = sample_jobs.get("greenhouse")
            if gh_job:
                gh_id = gh_job.get("source_job_id")
                cb = gh_job.get("company_board")
                print(f"\n[Greenhouse Probe] ID: {gh_id}, Board: {cb}")
                url = f"https://boards-api.greenhouse.io/v1/boards/{cb}/jobs/{gh_id}"
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        print(f"  Keys in Greenhouse job: {list(data.keys())}")
                        print(f"  pay in GH?: {data.get('pay')}")
                        print(f"  compensation in GH?: {data.get('compensation')}")
                        print(f"  metadata in GH?: {data.get('metadata')}")
                    else:
                        print(f"  GH fetch status: {resp.status_code}")
                except Exception as e:
                    print(f"  GH fetch error: {e}")

    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(audit())
