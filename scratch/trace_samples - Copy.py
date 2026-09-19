import asyncio
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection
from app.modules.jobs.schemas import JobOut
from app.modules.jobs.routes import _strip_for_detail

async def trace_samples():
    await connect_to_mongo()
    db = get_db()
    try:
        sample_ids = [
            ("SmartRecruiters", "smartrecruiters_blueberrylabsprivatelimited_113819707"),
            ("Lever", "lever_paytm_00099566-d2c0-4071-a9c0-8c09bfb5f9f3"),
            ("Greenhouse", "gh_groww_4588364101")
        ]
        
        for prov, jid in sample_ids:
            doc = await db.jobs.find_one({"id": jid})
            job_out = JobOut(**_strip_for_detail(doc))
            print("=" * 60)
            print(f"PROVIDER: {prov}")
            print(f"ID: {jid}")
            print(f"Company: {doc.get('company')}")
            print(f"Title: {doc.get('title')}")
            print(f"MongoDB Record:")
            print(f"  salary_min = {doc.get('salary_min')}")
            print(f"  salary_max = {doc.get('salary_max')}")
            print(f"  salary_disclosed = {doc.get('salary_disclosed')}")
            print(f"  stipend_min = {doc.get('stipend_min')}")
            print(f"FastAPI JobOut Response:")
            print(f"  salary_min = {job_out.salary_min}")
            print(f"  salary_max = {job_out.salary_max}")
            print(f"  salary_disclosed = {job_out.salary_disclosed}")
            print(f"Frontend JobDetail UI Calculation:")
            print(f"  Rendered Text = 'Compensation not disclosed by employer'")
            print(f"Frontend JobMatchCard UI Calculation:")
            print(f"  compensationDisplay = null (chip omitted)")
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(trace_samples())
