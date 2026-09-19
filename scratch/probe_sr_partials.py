import asyncio
import httpx

async def probe():
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Probe Bosch 744000147416769
        url = "https://api.smartrecruiters.com/v1/companies/BoschGroup/postings/744000147416769"
        res = await client.get(url)
        print("Bosch 744000147416769 status:", res.status_code)
        if res.status_code == 200:
            data = res.json()
            sections = data.get("jobAd", {}).get("sections", {})
            print("Bosch sections keys:", list(sections.keys()))
            job_desc = sections.get("jobDescription", {}).get("text", "")
            print("Bosch jobDescription length:", len(job_desc))

        # Probe Blueberry 107898226
        url2 = "https://api.smartrecruiters.com/v1/companies/BlueberryLabsPrivateLimited/postings/107898226"
        res2 = await client.get(url2)
        print("Blueberry 107898226 status:", res2.status_code)
        if res2.status_code == 200:
            data2 = res2.json()
            sections2 = data2.get("jobAd", {}).get("sections", {})
            print("Blueberry sections keys:", list(sections2.keys()))
            job_desc2 = sections2.get("jobDescription", {}).get("text", "")
            print("Blueberry jobDescription length:", len(job_desc2))

if __name__ == "__main__":
    asyncio.run(probe())
