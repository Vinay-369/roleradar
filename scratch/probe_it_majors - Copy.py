import asyncio
import httpx

majors = [
    ("TCS", "https://ibegin.tcs.com/iBegin/jobs/search"),
    ("Infosys", "https://career.infosys.com/joblist"),
    ("Wipro", "https://careers.wipro.com/careers-home/jobs"),
    ("Accenture", "https://www.accenture.com/api/sitecore/AccentureSearch/GetSearchJobs"),
    ("Cognizant", "https://careers.cognizant.com/global/en/search-results"),
    ("Capgemini", "https://www.capgemini.com/in-en/careers/job-search/"),
    ("HCLTech", "https://www.hcltech.com/careers/careers-in-india"),
    ("TechMahindra", "https://careers.techmahindra.com/"),
    ("LTIMindtree", "https://www.ltimindtree.com/careers/"),
]

async def check_major(client, name, url):
    try:
        r = await client.get(url, timeout=10.0, follow_redirects=True)
        return {
            "name": name,
            "status": r.status_code,
            "content_type": r.headers.get("content-type", ""),
            "has_json": "application/json" in r.headers.get("content-type", "").lower(),
            "final_url": str(r.url),
            "snippet": r.text[:200]
        }
    except Exception as e:
        return {"name": name, "status": "ERROR", "error": str(e)}

async def main():
    async with httpx.AsyncClient(headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }) as client:
        print("=== PROBING INDIAN IT MAJORS ===")
        for name, url in majors:
            res = await check_major(client, name, url)
            print(f"[{res.get('status')}] {name}: content_type={res.get('content_type')}, has_json={res.get('has_json')}, final_url={res.get('final_url')}")
            if res.get("status") == "ERROR":
                print(f"    Error: {res.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())
