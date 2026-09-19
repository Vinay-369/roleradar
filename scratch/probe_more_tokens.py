import asyncio
import httpx

more_gh = [
    "canonical", "nutanix", "redhat", "salesforce", "atlassian",
    "adobe", "uber", "walmart", "target", "cisco", "oracle",
    "servicenow", "splunk", "paloaltonetworks", "crowdstrike",
    "snowflake", "confluent", "hashicorp", "samsara", "rubrik",
    "cohesity", "purestorage", "dynatrace", "appdynamics",
    "pagerduty", "newrelic", "snyk", "cockroachlabs", "yugabyte",
    "instacart", "doordash", "pinterest", "reddit", "snap",
    "discord", "canva", "notion", "airtable", "miro", "grammarly"
]

more_lever = [
    "udaan", "lenskart", "nykaa", "rapido", "urbancompany",
    "unacademy", "scaler", "cultfit", "curefit", "spinny",
    "cars24", "zeta", "browserstack", "clevertap", "moengage"
]

more_sr = [
    "Visa", "PublicisSapient", "SchneiderElectric", "siemens",
    "WoltersKluwer", "Honeywell", "Hitachi", "Philips", "Continental",
    "Alstom", "Capgemini", "Wipro", "Infosys", "TCS", "Cognizant"
]

async def check_gh(client, token):
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    try:
        r = await client.get(url, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            jobs = data.get("jobs", [])
            in_jobs = [j for j in jobs if any(kw in (j.get("location", {}).get("name") or "").lower() for kw in ["india", "bengaluru", "bangalore", "mumbai", "delhi", "gurgaon", "noida", "hyderabad", "chennai", "pune"])]
            interns = [j for j in in_jobs if "intern" in (j.get("title") or "").lower()]
            return {"token": token, "status": 200, "total": len(jobs), "india": len(in_jobs), "interns": len(interns), "sample": [j.get("title") for j in in_jobs[:3]]}
        return {"token": token, "status": r.status_code}
    except Exception:
        return {"token": token, "status": "ERR"}

async def check_lever(client, token):
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    try:
        r = await client.get(url, timeout=5.0)
        if r.status_code == 200:
            jobs = r.json()
            in_jobs = [j for j in jobs if any(kw in (j.get("categories", {}).get("location") or "").lower() for kw in ["india", "bengaluru", "bangalore", "mumbai", "delhi", "gurgaon", "noida", "hyderabad", "chennai", "pune"])]
            interns = [j for j in in_jobs if "intern" in (j.get("text") or "").lower()]
            return {"token": token, "status": 200, "total": len(jobs), "india": len(in_jobs), "interns": len(interns), "sample": [j.get("text") for j in in_jobs[:3]]}
        return {"token": token, "status": r.status_code}
    except Exception:
        return {"token": token, "status": "ERR"}

async def check_sr(client, token):
    url = f"https://api.smartrecruiters.com/v1/companies/{token}/postings?country=in&limit=100"
    try:
        r = await client.get(url, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            jobs = data.get("content", [])
            total = data.get("totalFound", len(jobs))
            interns = [j for j in jobs if "intern" in (j.get("name") or "").lower()]
            return {"token": token, "status": 200, "total_in": total, "interns": len(interns), "sample": [j.get("name") for j in jobs[:3]]}
        return {"token": token, "status": r.status_code}
    except Exception:
        return {"token": token, "status": "ERR"}

async def main():
    async with httpx.AsyncClient(headers={"User-Agent": "RoleRadar-Research/1.0"}) as client:
        print("=== PROBING GREENHOUSE BATCH 2 ===")
        for t in more_gh:
            res = await check_gh(client, t)
            if res.get("status") == 200 and res.get("india", 0) > 0:
                print(f"  [GH 200] {t}: India={res['india']}, Interns={res['interns']}, sample={res['sample']}")

        print("\n=== PROBING LEVER BATCH 2 ===")
        for t in more_lever:
            res = await check_lever(client, t)
            if res.get("status") == 200 and res.get("india", 0) > 0:
                print(f"  [LEVER 200] {t}: India={res['india']}, Interns={res['interns']}, sample={res['sample']}")

        print("\n=== PROBING SMARTRECRUITERS BATCH 2 ===")
        for t in more_sr:
            res = await check_sr(client, t)
            if res.get("status") == 200 and res.get("total_in", 0) > 0:
                print(f"  [SR 200] {t}: India={res['total_in']}, Interns={res['interns']}, sample={res['sample']}")

if __name__ == "__main__":
    asyncio.run(main())
