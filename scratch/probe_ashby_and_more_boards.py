import asyncio
import httpx

test_ashby = [
    "zepto", "browserstack", "blinkit", "cred", "postman", "swiggy",
    "razorpay", "slice", "urbancompany", "fam", "khatabook", "groww"
]

test_greenhouse = [
    "razorpaysoftware", "swiggycareers", "swiggy1", "phonepe",
    "browserstack", "browserstacksoftware", "freshworksinc", "chargebee",
    "dreamplugtechnologies", "cred", "zomato", "blinkit", "urbancompany",
    "zeptonow", "zeptocareers", "inmobi", "postman", "airbnb", "figma",
    "stripe", "uber", "atlassian", "salesforce", "cisco", "oracle",
    "twilio", "canonical", "elastic", "mongodb", "cloudflare", "gitlab",
    "datadog", "snowflake", "palantir", "crowdstrike", "okta", "servicenow",
    "vmware", "nutanix", "thoughtworks", "target", "walmart", "intuit"
]

test_lever = [
    "paytm", "meesho", "cred", "fi", "urbancompany", "slice",
    "khatabook", "rapido", "pocketfm", "scaler", "unacademy",
    "curefit", "cultfit", "lenskart", "nykaa", "udaan", "zerodha"
]

async def check_ashby(client, org):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{org}"
    try:
        r = await client.get(url, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            jobs = data.get("jobs", [])
            in_jobs = [j for j in jobs if any(kw in (j.get("location") or "").lower() for kw in ["india", "bengaluru", "bangalore", "mumbai", "delhi", "gurgaon", "noida", "hyderabad", "pune", "chennai"])]
            return {"org": org, "status": 200, "total": len(jobs), "india": len(in_jobs)}
        return {"org": org, "status": r.status_code}
    except Exception as e:
        return {"org": org, "status": "ERR", "error": str(e)}

async def check_gh(client, token):
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    try:
        r = await client.get(url, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            jobs = data.get("jobs", [])
            in_jobs = [j for j in jobs if any(kw in (j.get("location", {}).get("name") or "").lower() for kw in ["india", "bengaluru", "bangalore", "mumbai", "delhi", "gurgaon", "noida", "hyderabad", "pune", "chennai"])]
            interns = [j for j in in_jobs if "intern" in (j.get("title") or "").lower()]
            return {"token": token, "status": 200, "total": len(jobs), "india": len(in_jobs), "interns": len(interns), "sample": [j.get("title") for j in in_jobs[:3]]}
        return {"token": token, "status": r.status_code}
    except Exception as e:
        return {"token": token, "status": "ERR"}

async def check_lever(client, token):
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    try:
        r = await client.get(url, timeout=5.0)
        if r.status_code == 200:
            jobs = r.json()
            in_jobs = [j for j in jobs if any(kw in (j.get("categories", {}).get("location") or "").lower() for kw in ["india", "bengaluru", "bangalore", "mumbai", "delhi", "gurgaon", "noida", "hyderabad", "chennai"])]
            interns = [j for j in in_jobs if "intern" in (j.get("text") or "").lower()]
            return {"token": token, "status": 200, "total": len(jobs), "india": len(in_jobs), "interns": len(interns), "sample": [j.get("text") for j in in_jobs[:3]]}
        return {"token": token, "status": r.status_code}
    except Exception as e:
        return {"token": token, "status": "ERR"}

async def main():
    async with httpx.AsyncClient(headers={"User-Agent": "RoleRadar-Research/1.0"}) as client:
        print("=== PROBING ASHBY ===")
        for org in test_ashby:
            res = await check_ashby(client, org)
            if res.get("status") == 200:
                print(f"  [ASHBY 200] {org}: total={res['total']}, India={res['india']}")

        print("\n=== PROBING GREENHOUSE TOKENS ===")
        for token in test_greenhouse:
            res = await check_gh(client, token)
            if res.get("status") == 200 and res.get("india", 0) > 0:
                print(f"  [GH 200] {token}: India={res['india']}, Interns={res['interns']}, samples={res['sample']}")

        print("\n=== PROBING LEVER TOKENS ===")
        for token in test_lever:
            res = await check_lever(client, token)
            if res.get("status") == 200 and res.get("india", 0) > 0:
                print(f"  [LEVER 200] {token}: India={res['india']}, Interns={res['interns']}, samples={res['sample']}")

if __name__ == "__main__":
    asyncio.run(main())
