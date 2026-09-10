import asyncio
import httpx
import json

candidate_greenhouse = [
    ("razorpay", "Razorpay"),
    ("swiggy", "Swiggy"),
    ("phonepe", "PhonePe"),
    ("browserstack", "BrowserStack"),
    ("freshworks", "Freshworks"),
    ("chargebee", "Chargebee"),
    ("moengage", "MoEngage"),
    ("clevertap", "CleverTap"),
    ("hasura", "Hasura"),
    ("dream11", "Dream11"),
    ("zepto", "Zepto"),
    ("urbancompany", "Urban Company"),
    ("slice", "Slice"),
    ("khatabook", "Khatabook"),
]

candidate_lever = [
    ("hotstar", "Disney+ Hotstar"),
    ("coindcx", "CoinDCX"),
    ("cars24", "Cars24"),
    ("jupiter", "Jupiter Money"),
    ("upstox", "Upstox"),
    ("mpl", "Mobile Premier League"),
    ("jar", "Jar App"),
    ("spinny", "Spinny"),
]

candidate_smartrecruiters = [
    ("publicissapient", "Publicis Sapient"),
    ("visa", "Visa"),
    ("siemens", "Siemens"),
    ("schneiderelectric", "Schneider Electric"),
    ("wolterskluwer", "Wolters Kluwer"),
]

async def probe_gh(client, token, company):
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    try:
        r = await client.get(url, timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            jobs = data.get("jobs", [])
            # Count India jobs
            india_jobs = [
                j for j in jobs
                if any(kw in (j.get("location", {}).get("name") or "").lower() for kw in ["india", "bengaluru", "bangalore", "mumbai", "pune", "gurgaon", "noida", "hyderabad", "chennai"])
            ]
            interns = [
                j for j in india_jobs
                if "intern" in (j.get("title") or "").lower()
            ]
            return {
                "token": token, "company": company, "status": 200,
                "total_jobs": len(jobs), "india_jobs": len(india_jobs), "india_interns": len(interns),
                "sample_titles": [j.get("title") for j in india_jobs[:5]]
            }
        return {"token": token, "company": company, "status": r.status_code, "error": r.text[:100]}
    except Exception as e:
        return {"token": token, "company": company, "status": "ERROR", "error": str(e)}

async def probe_lever(client, token, company):
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    try:
        r = await client.get(url, timeout=10.0)
        if r.status_code == 200:
            jobs = r.json()
            india_jobs = [
                j for j in jobs
                if any(kw in (j.get("categories", {}).get("location") or "").lower() for kw in ["india", "bengaluru", "bangalore", "mumbai", "pune", "gurgaon", "noida", "hyderabad", "chennai"])
            ]
            interns = [
                j for j in india_jobs
                if "intern" in (j.get("text") or "").lower() or (j.get("categories", {}).get("commitment") or "").lower() == "intern"
            ]
            return {
                "token": token, "company": company, "status": 200,
                "total_jobs": len(jobs), "india_jobs": len(india_jobs), "india_interns": len(interns),
                "sample_titles": [j.get("text") for j in india_jobs[:5]]
            }
        return {"token": token, "company": company, "status": r.status_code, "error": r.text[:100]}
    except Exception as e:
        return {"token": token, "company": company, "status": "ERROR", "error": str(e)}

async def probe_sr(client, token, company):
    url = f"https://api.smartrecruiters.com/v1/companies/{token}/postings?country=in&limit=100"
    try:
        r = await client.get(url, timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            jobs = data.get("content", [])
            total = data.get("totalFound", len(jobs))
            interns = [j for j in jobs if "intern" in (j.get("name") or "").lower()]
            return {
                "token": token, "company": company, "status": 200,
                "total_in_country": total, "fetched": len(jobs), "interns": len(interns),
                "sample_titles": [j.get("name") for j in jobs[:5]]
            }
        return {"token": token, "company": company, "status": r.status_code, "error": r.text[:100]}
    except Exception as e:
        return {"token": token, "company": company, "status": "ERROR", "error": str(e)}

async def main():
    async with httpx.AsyncClient(headers={"User-Agent": "RoleRadar-Probe/1.0"}) as client:
        print("--- 1. PROBING GREENHOUSE CANDIDATES ---")
        for token, company in candidate_greenhouse:
            res = await probe_gh(client, token, company)
            print(f"[{res.get('status')}] {company} ({token}): total={res.get('total_jobs')}, India={res.get('india_jobs')}, Interns={res.get('india_interns')}")
            if res.get("sample_titles"):
                print(f"    Samples: {res['sample_titles'][:3]}")

        print("\n--- 2. PROBING LEVER CANDIDATES ---")
        for token, company in candidate_lever:
            res = await probe_lever(client, token, company)
            print(f"[{res.get('status')}] {company} ({token}): total={res.get('total_jobs')}, India={res.get('india_jobs')}, Interns={res.get('india_interns')}")
            if res.get("sample_titles"):
                print(f"    Samples: {res['sample_titles'][:3]}")

        print("\n--- 3. PROBING SMARTRECRUITERS CANDIDATES ---")
        for token, company in candidate_smartrecruiters:
            res = await probe_sr(client, token, company)
            print(f"[{res.get('status')}] {company} ({token}): total_in_in={res.get('total_in_country')}, Interns={res.get('interns')}")
            if res.get("sample_titles"):
                print(f"    Samples: {res['sample_titles'][:3]}")

if __name__ == "__main__":
    asyncio.run(main())
