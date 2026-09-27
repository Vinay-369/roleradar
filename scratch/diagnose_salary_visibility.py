"""
Diagnose why salary is not visible on the website.
This script checks the data flow from database to frontend.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

async def diagnose_salary_visibility():
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core.config import get_settings
    from app.db.mongo import Collections
    from app.modules.jobs.routes import _strip_for_list
    from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text

    print("=" * 80)
    print("SALARY VISIBILITY DIAGNOSTIC")
    print("=" * 80)

    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    # Get sample jobs
    cursor = db[Collections.JOBS].find({}).limit(5)
    jobs = await cursor.to_list(length=5)

    print(f"Sample jobs from database: {len(jobs)}")

    # Check what's in the database
    print("\n--- DATABASE CONTENT ---")
    for i, job in enumerate(jobs, 1):
        print(f"\n{i}. {job.get('title', 'Unknown')[:40]} @ {job.get('company', 'Unknown')[:20]}")
        print(f"   salary_min: {job.get('salary_min')}")
        print(f"   salary_max: {job.get('salary_max')}")
        print(f"   stipend_min: {job.get('stipend_min')}")
        print(f"   compensation_text: {job.get('compensation_text')}")
        print(f"   compensation_type: {job.get('compensation_type')}")
        print(f"   salary_disclosed: {job.get('salary_disclosed')}")

        # Check if compensation extraction would find data
        jd_text = job.get('jd_text') or job.get('description') or ''
        raw_payload = job.get('raw_payload')
        is_intern = (
            job.get('job_type') == 'internship' or
            job.get('opportunity_type') == 'INTERNSHIP' or
            'intern' in (job.get('title') or '').lower()
        )

        if jd_text:
            comp = extract_compensation_from_payload_and_text(
                text=jd_text,
                raw_payload=raw_payload,
                is_internship=is_intern,
            )
            print(f"   Extraction test:")
            print(f"     Type: {comp.compensation_type}")
            print(f"     Salary min/max: {comp.salary_min} - {comp.salary_max}")
            print(f"     Stipend: {comp.stipend_min} - {comp.stipend_max}")
            print(f"     Text: {comp.compensation_text}")

            if comp.compensation_type in ['NUMERIC', 'QUALITATIVE']:
                print(f"   → Would add to database: {comp.salary_min or comp.stipend_min}")
            else:
                print(f"   → No compensation found in text")

    await client.close()
    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(diagnose_salary_visibility())