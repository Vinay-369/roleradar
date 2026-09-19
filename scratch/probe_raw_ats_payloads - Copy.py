import asyncio
import json
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

import httpx
from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection

async def probe_ats_payloads():
    await connect_to_mongo()
    db = get_db()
    
    try:
        # Sample distinct companies for each provider
        query = {
            "verification_status": "VERIFIED_ACTIVE",
            "country": "India",
            "source": {"$in": ["smartrecruiters", "lever", "greenhouse"]}
        }
        all_jobs = await db.jobs.find(query).to_list(length=10000)
        
        # Pick 3 jobs per company across providers
        by_company = {}
        for j in all_jobs:
            k = (j["source"], j["company"], j.get("company_board"))
            if k not in by_company:
                by_company[k] = j
                
        print(f"Distinct provider-company boards in India: {len(by_company)}")
        for (src, comp, board) in by_company.keys():
            print(f"  - [{src}] {comp} (board: {board})")

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. SmartRecruiters
            print("\n" + "=" * 60)
            print("PROBING SMARTRECRUITERS RAW PAYLOADS")
            print("=" * 60)
            sr_jobs = [j for (src, comp, board), j in by_company.items() if src == "smartrecruiters"]
            for j in sr_jobs[:4]:
                board = j.get("company_board") or j.get("company")
                jid = j.get("source_job_id")
                url = f"https://api.smartrecruiters.com/v1/companies/{board}/postings/{jid}"
                res = await client.get(url)
                if res.status_code == 200:
                    d = res.json()
                    # Check any keys mentioning pay, salary, comp, wage, stipend, rate
                    salary_keys = {k: v for k, v in d.items() if any(w in k.lower() for w in ["salary", "comp", "pay", "wage", "stipend", "rate"])}
                    # Check custom fields
                    custom = d.get("customField") or []
                    custom_salary = [cf for cf in custom if any(w in str(cf).lower() for w in ["salary", "comp", "pay", "wage", "stipend", "rate", "ctc"])]
                    print(f"[{j['company']} - {j['title'][:30]}]")
                    print(f"  matching top-level keys: {salary_keys}")
                    print(f"  matching custom fields: {custom_salary}")
                else:
                    print(f"[{j['company']}] HTTP {res.status_code}")

            # 2. Lever
            print("\n" + "=" * 60)
            print("PROBING LEVER RAW PAYLOADS")
            print("=" * 60)
            lever_jobs = [j for (src, comp, board), j in by_company.items() if src == "lever"]
            for j in lever_jobs[:4]:
                board = j.get("company_board")
                jid = j.get("source_job_id")
                url = f"https://api.lever.co/v0/postings/{board}/{jid}"
                res = await client.get(url)
                if res.status_code == 200:
                    d = res.json()
                    salary_keys = {k: v for k, v in d.items() if any(w in k.lower() for w in ["salary", "comp", "pay", "wage", "stipend", "rate"])}
                    print(f"[{j['company']} - {j['title'][:30]}]")
                    print(f"  matching top-level keys: {salary_keys}")
                    print(f"  salaryRange: {d.get('salaryRange')}")
                    print(f"  salaryDescription: {d.get('salaryDescription')}")
                else:
                    print(f"[{j['company']}] HTTP {res.status_code}")

            # 3. Greenhouse
            print("\n" + "=" * 60)
            print("PROBING GREENHOUSE RAW PAYLOADS")
            print("=" * 60)
            gh_jobs = [j for (src, comp, board), j in by_company.items() if src == "greenhouse"]
            for j in gh_jobs[:4]:
                board = j.get("company_board")
                jid = j.get("source_job_id")
                url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{jid}"
                res = await client.get(url)
                if res.status_code == 200:
                    d = res.json()
                    salary_keys = {k: v for k, v in d.items() if any(w in k.lower() for w in ["salary", "comp", "pay", "wage", "stipend", "rate"])}
                    print(f"[{j['company']} - {j['title'][:30]}]")
                    print(f"  matching top-level keys: {salary_keys}")
                    print(f"  pay: {d.get('pay')}")
                    print(f"  metadata matching salary: {[m for m in (d.get('metadata') or []) if any(w in str(m).lower() for w in ['salary', 'comp', 'pay', 'wage', 'stipend', 'rate', 'ctc'])]}")
                else:
                    print(f"[{j['company']}] HTTP {res.status_code}")

    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(probe_ats_payloads())
