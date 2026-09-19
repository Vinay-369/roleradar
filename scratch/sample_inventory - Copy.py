import asyncio
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection

async def check():
    await connect_to_mongo()
    db = get_db()
    try:
        for prov in ["smartrecruiters", "lever", "greenhouse"]:
            base = {"verification_status": "VERIFIED_ACTIVE", "country": "India", "source": prov}
            total = await db.jobs.count_documents(base)
            
            # Check all jobs
            all_docs = await db.jobs.find(base).to_list(length=500)
            interns = [
                d for d in all_docs
                if d.get("opportunity_type") == "INTERNSHIP"
                or d.get("job_type") == "internship"
                or "intern" in (d.get("title") or "").lower()
            ]
            jobs = [d for d in all_docs if d not in interns]
            print(f"{prov}: total={total}, jobs={len(jobs)}, interns={len(interns)}")
            if interns:
                for it in interns:
                    print(f"   Internship: {it.get('id')} | {it.get('company')} | {it.get('title')}")
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(check())
