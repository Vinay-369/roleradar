import asyncio
import json
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection

# Strict regex patterns requiring at least one digit and currency/CTC marker
STRICT_NUMERIC_SALARY_PATTERNS = [
    # ₹ 5,00,000 or INR 500000 or Rs. 500000 or Rs 50,000
    re.compile(r"(?:₹|INR|Rs\.?)\s*([0-9][0-9,]*)(?:\s*(?:-|–|to)\s*(?:₹|INR|Rs\.?)?\s*([0-9][0-9,]*))?\s*(?:lpa|per\s*annum|p\.?a\.?|per\s*year|per\s*month|/month|pm)?\b", re.IGNORECASE),
    # 6-12 LPA or 6 to 12 Lacs or 8 LPA
    re.compile(r"\b([0-9]+(?:\.[0-9]+)?)\s*(?:-|–|to)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:lpa|lacs?|lakhs?)\b", re.IGNORECASE),
    re.compile(r"\b([0-9]+(?:\.[0-9]+)?)\s*(?:lpa|lacs?|lakhs?)\b", re.IGNORECASE),
    # CTC: 10,00,000 or Stipend: 25,000
    re.compile(r"\b(?:ctc|salary|stipend|package|remuneration)\s*[:\-]\s*(?:₹|INR|Rs\.?)?\s*([0-9][0-9,]*)\b", re.IGNORECASE),
    # 25k/month or 25k pm
    re.compile(r"\b([0-9]+)\s*k\s*/\s*(?:month|pm)\b", re.IGNORECASE),
]

# Non-numeric compensation phrases
NON_NUMERIC_PATTERNS = [
    re.compile(r"\b(?:competitive|best\s*in\s*industry|market\s*standard|attractive|industry\s*standard|commensurate\s*with\s*experience|as\s*per\s*market|competitive\s*salary|best\s*in\s*class)\b", re.IGNORECASE),
    re.compile(r"\b(?:salary|compensation|remuneration|stipend)\s*(?:is\s*)?(?:not\s*a\s*constraint|negotiable|competitive|commensurate)\b", re.IGNORECASE),
]

async def run_audit():
    await connect_to_mongo()
    db = get_db()
    try:
        query = {
            "verification_status": "VERIFIED_ACTIVE",
            "country": "India",
            "source": {"$in": ["smartrecruiters", "lever", "greenhouse"]}
        }
        
        cursor = db.jobs.find(query)
        all_jobs = await cursor.to_list(length=10000)
        
        print("=" * 80)
        print("AUTHORITATIVE RE-CALCULATION OF 587 INDIAN LIVE OPPORTUNITIES")
        print("=" * 80)
        print(f"Total Indian VERIFIED_ACTIVE records in Mongo: {len(all_jobs)}")
        
        by_provider = defaultdict(list)
        for j in all_jobs:
            by_provider[j["source"]].append(j)
            
        for p, jobs in by_provider.items():
            print(f"  - {p}: {len(jobs)}")

        # Check internships
        internships = [j for j in all_jobs if j.get("opportunity_type") == "INTERNSHIP" or "intern" in (j.get("job_type") or "").lower()]
        full_time = [j for j in all_jobs if j not in internships]
        
        print(f"\nBreakdown by Type:")
        print(f"  - Full-time jobs: {len(full_time)}")
        print(f"  - Internships: {len(internships)}")

        print("\n" + "=" * 80)
        print("DETAILED SCAN FOR NUMERIC SALARY & NON-NUMERIC COMPENSATION")
        print("=" * 80)
        
        genuine_numeric = []
        non_numeric_disclosed = []
        unusable_salary = []
        not_disclosed = []

        for j in all_jobs:
            jid = j.get("id")
            title = j.get("title")
            company = j.get("company")
            src = j.get("source")
            desc = (j.get("description") or "") + " " + (j.get("raw_html") or "")
            
            # Check mongo fields
            s_min = j.get("salary_min")
            s_max = j.get("salary_max")
            s_disc = j.get("salary_disclosed")
            stipend = j.get("stipend_min")

            # Check if text contains numeric salary
            found_numeric = []
            for pat in STRICT_NUMERIC_SALARY_PATTERNS:
                matches = pat.finditer(desc)
                for m in matches:
                    raw_snippet = desc[max(0, m.start() - 25):min(len(desc), m.end() + 25)]
                    # filter out year/month/version numbers
                    match_str = m.group(0).strip()
                    # verify it's really money/CTC
                    # e.g., "3-5 years" or "version 2.0" or "8-14 years" should not pass
                    if re.search(r"\b(?:years?|yrs?|months?\s*experience|exp)\b", raw_snippet, re.I):
                        continue
                    if re.search(r"ISO|IEC|\.0\.\d+|v\d+", match_str, re.I):
                        continue
                    found_numeric.append((match_str, raw_snippet))

            if found_numeric or (s_min and s_min > 0) or (s_max and s_max > 0) or (stipend and stipend > 0):
                genuine_numeric.append({
                    "id": jid,
                    "company": company,
                    "title": title,
                    "source": src,
                    "mongo_salary": (s_min, s_max, s_disc, stipend),
                    "matches": found_numeric,
                })
            else:
                # Check for non-numeric compensation
                found_non_numeric = []
                for pat in NON_NUMERIC_PATTERNS:
                    m = pat.search(desc)
                    if m:
                        snippet = desc[max(0, m.start() - 20):min(len(desc), m.end() + 20)]
                        found_non_numeric.append((m.group(0), snippet))
                
                if found_non_numeric:
                    non_numeric_disclosed.append({
                        "id": jid,
                        "company": company,
                        "title": title,
                        "source": src,
                        "matches": found_non_numeric,
                    })
                else:
                    not_disclosed.append({
                        "id": jid,
                        "company": company,
                        "title": title,
                        "source": src,
                    })

        print(f"\nOverall Summary:")
        print(f"  - Genuine Numeric Salary Disclosed: {len(genuine_numeric)}")
        print(f"  - Non-numeric Compensation Disclosed: {len(non_numeric_disclosed)}")
        print(f"  - Unusable / Malformed Salary: {len(unusable_salary)}")
        print(f"  - Salary Not Disclosed by Employer: {len(not_disclosed)}")
        print(f"  - Total: {len(genuine_numeric) + len(non_numeric_disclosed) + len(unusable_salary) + len(not_disclosed)}")

        if genuine_numeric:
            print("\nGENUINE NUMERIC SALARY RECORDS FOUND:")
            for item in genuine_numeric:
                print(f"  [{item['source']}] {item['company']} - {item['title']} ({item['id']}):")
                print(f"    Matches: {item['matches']}")
                print(f"    Mongo fields: {item['mongo_salary']}")
        else:
            print("\nNO NUMERIC SALARY DISCLOSED ACROSS ANY OF THE 587 INDIAN LIVE RECORDS.")

        print(f"\nNON-NUMERIC COMPENSATION SAMPLES ({len(non_numeric_disclosed)} total):")
        for item in non_numeric_disclosed[:5]:
            print(f"  [{item['source']}] {item['company']} - {item['title']}: {item['matches'][0]}")

        # Internships Breakdown
        print("\n" + "=" * 80)
        print("INTERNSHIPS SPECIFIC AUDIT")
        print("=" * 80)
        print(f"Total Indian Live Internships: {len(internships)}")
        for intern in internships:
            idesc = (intern.get("description") or "") + " " + (intern.get("raw_html") or "")
            print(f"\nInternship ID: {intern.get('id')}")
            print(f"  Title: {intern.get('title')}")
            print(f"  Company: {intern.get('company')}")
            print(f"  Source: {intern.get('source')}")
            print(f"  Mongo stipend_min: {intern.get('stipend_min')}")
            print(f"  Mongo stipend_max: {intern.get('stipend_max')}")
            print(f"  Mongo salary_disclosed: {intern.get('salary_disclosed')}")
            
            # Check for stipend in text
            stipend_matches = re.findall(r"(?:stipend|salary|remuneration|pay|allowance)[^\.\n,]*", idesc, re.I)
            print(f"  Text mentions of stipend/pay: {stipend_matches[:3] if stipend_matches else 'None'}")

    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(run_audit())
