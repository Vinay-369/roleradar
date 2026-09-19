import asyncio
import httpx
import json

async def check_all_23():
    with open("scratch/partials_detail.json", "r", encoding="utf-8") as f:
        partials = json.load(f)

    async with httpx.AsyncClient(timeout=15.0) as client:
        for p in partials:
            # Parse provider board and job_id
            job_id_full = p["id"] # e.g. smartrecruiters_boschgroup_744000147416769
            parts = job_id_full.split("_")
            board = parts[1]
            jid = parts[2]
            url = f"https://api.smartrecruiters.com/v1/companies/{board}/postings/{jid}"
            try:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    sections = data.get("jobAd", {}).get("sections", {})
                    jd_len = len(sections.get("jobDescription", {}).get("text", ""))
                    qual_len = len(sections.get("qualifications", {}).get("text", ""))
                    print(f"SUCCESS: {job_id_full} -> JD: {jd_len} chars, Quals: {qual_len} chars")
                else:
                    print(f"FAILED ({res.status_code}): {job_id_full}")
            except Exception as e:
                print(f"ERROR: {job_id_full} -> {e}")

if __name__ == "__main__":
    asyncio.run(check_all_23())
