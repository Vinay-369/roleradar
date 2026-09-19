import asyncio
import json
import sys
sys.path.insert(0, ".")

from app.modules.jobs.smartrecruiters_provider import SmartRecruitersJobProvider

async def main():
    sr = SmartRecruitersJobProvider()
    # Fetch a few Blueberry Labs job IDs from SmartRecruiters
    # Let's inspect board "BlueberryLabsPrivateLimited"
    data = await sr.fetch_specific_opening("BlueberryLabsPrivateLimited", "101534578")
    if data:
        print("=== JOB 101534578 ===")
        print("Title:", data.get("name"))
        jobAd = data.get("jobAd", {})
        sections = jobAd.get("sections", {})
        for k, v in sections.items():
            print(f"\n--- Section: {k} ---")
            print("Title:", repr(v.get("title")))
            print("Text (first 500 chars):", repr(v.get("text"))[:500])

        norm = sr.normalize_smartrecruiters_job(data, "BlueberryLabsPrivateLimited")
        print("\n=== NORMALIZED DESCRIPTION ===")
        print(norm.get("description"))

if __name__ == "__main__":
    asyncio.run(main())
