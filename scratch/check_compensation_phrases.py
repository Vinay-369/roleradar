import asyncio
import json
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection

COMP_PHRASES = [
    re.compile(r"\b(?:best\s*in\s*industry|competitive|attractive|industry\s*standard|market\s*standard|commensurate\s*with\s*experience)\s+(?:salary|compensation|package|stipend|pay|remuneration)\b", re.I),
    re.compile(r"\b(?:salary|compensation|package|stipend|remuneration)\s*[:\-]?\s*(?:is\s*)?(?:competitive|attractive|best\s*in\s*industry|negotiable|commensurate|as\s*per\s*industry|as\s*per\s*market)\b", re.I),
]

# Genuine numeric salary pattern where CTC / salary / stipend is explicitly stated with numbers
GENUINE_NUMERIC_SALARY_PATTERNS = [
    re.compile(r"\b(?:ctc|salary|stipend|package|remuneration|fixed\s*pay)\s*[:\-]\s*(?:₹|INR|Rs\.?)?\s*([0-9][0-9,.]*)\s*(?:lpa|lac|lacs|lakh|lakhs|per\s*annum|p\.?a\.?|per\s*month|pm|k)?\b", re.I),
    re.compile(r"\b(?:₹|INR|Rs\.?)\s*([0-9][0-9,.]*)\s*(?:-|–|to)\s*(?:₹|INR|Rs\.?)?\s*([0-9][0-9,.]*)\s*(?:lpa|per\s*annum|p\.?a\.?|per\s*year|per\s*month|pm)\b", re.I),
    re.compile(r"\b([0-9]+(?:\.[0-9]+)?)\s*(?:-|–|to)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:lpa|lacs?|lakhs?)\s*(?:ctc|salary|package|per\s*annum)?\b", re.I),
]

async def check():
    await connect_to_mongo()
    db = get_db()
    try:
        query = {
            "verification_status": "VERIFIED_ACTIVE",
            "country": "India",
            "source": {"$in": ["smartrecruiters", "lever", "greenhouse"]}
        }
        all_jobs = await db.jobs.find(query).to_list(length=10000)
        
        numeric_jobs = []
        non_numeric_jobs = []
        
        for j in all_jobs:
            desc = (j.get("description") or "") + " " + (j.get("raw_html") or "")
            
            # Check numeric
            found_num = []
            for pat in GENUINE_NUMERIC_SALARY_PATTERNS:
                for m in pat.finditer(desc):
                    raw = desc[max(0, m.start() - 30):min(len(desc), m.end() + 30)]
                    # filter out company revenue or years of experience
                    if not re.search(r"sales\s*of|revenue\s*of|crores|euro|billion|years?|yrs?|offering|loan", raw, re.I):
                        found_num.append((m.group(0), raw))
            
            if found_num:
                numeric_jobs.append((j, found_num))
            else:
                found_comp = []
                for pat in COMP_PHRASES:
                    for m in pat.finditer(desc):
                        found_comp.append(m.group(0))
                if found_comp:
                    non_numeric_jobs.append((j, found_comp))

        print(f"Total Indian Live: {len(all_jobs)}")
        print(f"Genuine Numeric Salary in Description: {len(numeric_jobs)}")
        print(f"Non-Numeric Compensation in Description: {len(non_numeric_jobs)}")
        print(f"Undisclosed (no salary info at all): {len(all_jobs) - len(numeric_jobs) - len(non_numeric_jobs)}")
        
        if numeric_jobs:
            print("\nNUMERIC SALARY JOBS:")
            for j, matches in numeric_jobs:
                print(f"  [{j.get('source')}] {j.get('company')} - {j.get('title')} ({j.get('id')}):")
                for m, raw in matches:
                    print(f"    Match: {m} | Context: {raw.strip()}")
                    
        print("\nNON-NUMERIC COMPENSATION JOBS:")
        by_src_non_num = defaultdict(list)
        for j, matches in non_numeric_jobs:
            by_src_non_num[j.get("source")].append((j, matches))
            
        for src, items in by_src_non_num.items():
            print(f"  Provider {src}: {len(items)} jobs")
            for j, matches in items[:3]:
                print(f"    - {j.get('company')} - {j.get('title')}: {matches}")

    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(check())
