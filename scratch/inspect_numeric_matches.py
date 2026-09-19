import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "backend")

from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection

async def main():
    await connect_to_mongo()
    db = get_db()
    try:
        query = {
            "verification_status": "VERIFIED_ACTIVE",
            "country": "India",
            "source": {"$in": ["smartrecruiters", "lever", "greenhouse"]},
            "compensation_type": "NUMERIC"
        }
        cursor = db.jobs.find(query)
        async for job in cursor:
            print(f"ID: {job.get('id')}")
            print(f"Provider: {job.get('source')} | Company: {job.get('company')} | Title: {job.get('title')}")
            print(f"Comp text: {job.get('compensation_text')}")
            print(f"Salary min/max: {job.get('salary_min')} / {job.get('salary_max')}")
            print(f"Stipend min: {job.get('stipend_min')}")
            # Snippet of description where match happened
            desc = (job.get('description') or '') + ' ' + (job.get('raw_html') or '')
            ct = job.get('compensation_text') or ''
            print(f"Description snippet around match:")
            # Find any numbers in ct
            import re
            m = re.search(r"(\d+)", ct)
            if m:
                pos = desc.find(m.group(1))
                if pos != -1:
                    print(f"  ...{desc[max(0, pos-100):min(len(desc), pos+100)]}...")
            print("-" * 60)
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
