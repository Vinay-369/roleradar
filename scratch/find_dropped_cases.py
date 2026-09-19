import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "backend")

from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection
from app.modules.jobs.routes import _strip_for_detail
from app.modules.jobs.schemas import JobOut
from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text
import re

QUALITATIVE_COMP_PATTERNS = [
    re.compile(r"\b(?:best\s*in\s*industry|competitive|attractive|industry\s*standard|market\s*standard|commensurate\s*with\s*experience)\s+(?:salary|compensation|package|stipend|pay|remuneration)\b", re.I),
    re.compile(r"\b(?:salary|compensation|package|stipend|remuneration)\s*[:\-]?\s*(?:is\s*)?(?:competitive|attractive|best\s*in\s*industry|negotiable|commensurate|as\s*per\s*industry|as\s*per\s*market)\b", re.I),
]

async def check():
    await connect_to_mongo()
    db = get_db()
    try:
        query = {
            "verification_status": "VERIFIED_ACTIVE",
            "country": "India",
            "source": {"$in": ["smartrecruiters", "lever", "greenhouse"]}
        }
        all_jobs = await db.jobs.find(query).to_list(length=10000)
        for job in all_jobs:
            desc = (job.get("description") or "") + " " + (job.get("raw_html") or "")
            matches = []
            for p in QUALITATIVE_COMP_PATTERNS:
                for m in p.finditer(desc):
                    matches.append(m.group(0))
            if matches:
                job_out = JobOut(**_strip_for_detail(job))
                if not job_out.compensation_text and not job_out.salary_disclosed:
                    print(f"DROPPED: {job.get('id')} | {job.get('company')} | {job.get('title')}")
                    print(f"  Matches: {matches}")
                    comp = extract_compensation_from_payload_and_text(desc)
                    print(f"  Direct comp extraction: {comp}")
                    print("-" * 50)
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(check())
