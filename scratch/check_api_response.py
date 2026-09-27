"""
Quick diagnostic: Check what data is being returned by the API.
"""
import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

async def check_api_response():
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core.config import get_settings
    from app.db.mongo import Collections
    from app.modules.jobs.routes import _strip_for_list, _attach_compensation_meta

    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    # Get a few sample jobs
    cursor = db[Collections.JOBS].find({}).limit(5)
    jobs = await cursor.to_list(length=5)

    print("=" * 70)
    print("CHECKING API RESPONSE DATA")
    print("=" * 70)

    for i, job in enumerate(jobs, 1):
        print(f"\n{i}. {job.get('title', 'Unknown')[:50]} @ {job.get('company', 'Unknown')}")
        print("-" * 70)

        # Show raw database fields
        print("\nRAW DATABASE FIELDS:")
        print(f"  salary_min: {job.get('salary_min')}")
        print(f"  salary_max: {job.get('salary_max')}")
        print(f"  stipend_min: {job.get('stipend_min')}")
        print(f"  stipend_max: {job.get('stipend_max')}")
        print(f"  stipend: {job.get('stipend')}")
        print(f"  compensation_text: {job.get('compensation_text')}")
        print(f"  compensation_type: {job.get('compensation_type')}")
        print(f"  salary_disclosed: {job.get('salary_disclosed')}")

        # Simulate what _strip_for_list does
        print("\nAFTER _strip_for_list (simulated):")
        processed_job = _strip_for_list(dict(job))
        print(f"  salary_min: {processed_job.get('salary_min')}")
        print(f"  salary_max: {processed_job.get('salary_max')}")
        print(f"  stipend_min: {processed_job.get('stipend_min')}")
        print(f"  stipend_max: {processed_job.get('stipend_max')}")
        print(f"  stipend: {processed_job.get('stipend')}")
        print(f"  compensation_text: {processed_job.get('compensation_text')}")
        print(f"  compensation_type: {processed_job.get('compensation_type')}")

        # Show what would be sent to frontend
        print("\nJSON KEYS THAT WOULD BE SENT TO FRONTEND:")
        relevant_keys = [k for k in processed_job.keys() if 'salary' in k or 'stipend' in k or 'compensation' in k]
        for key in relevant_keys:
            print(f"  {key}: {processed_job.get(key)}")

    await client.close()

if __name__ == "__main__":
    asyncio.run(check_api_response())
