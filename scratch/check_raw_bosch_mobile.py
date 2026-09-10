import asyncio
import sys
sys.path.insert(0, "backend")

from app.modules.jobs.smartrecruiters_provider import SmartRecruitersJobProvider, _clean_html_description

async def check_raw_sr():
    provider = SmartRecruitersJobProvider()
    detail = await provider.fetch_specific_opening("boschgroup", "744000147203758")
    if not detail:
        print("Could not fetch specific opening from API")
        return

    job_ad = detail.get("jobAd", {})
    sections = job_ad.get("sections", {})
    for k, v in sections.items():
        print(f"=== SECTION: {k} ({v.get('title')}) ===")
        raw_html = v.get("text", "")
        print("RAW HTML (first 500 chars):", repr(raw_html[:500]))
        cleaned = _clean_html_description(raw_html)
        print("CLEANED (first 500 chars):", repr(cleaned[:500]))

if __name__ == "__main__":
    asyncio.run(check_raw_sr())
