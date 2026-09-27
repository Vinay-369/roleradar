"""
Test what the API actually returns for jobs with compensation data
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

async def test_api_response():
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core.config import get_settings
    from app.db.mongo import Collections

    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    print("=" * 80)
    print("TESTING API RESPONSE FOR JOBS WITH COMPENSATION")
    print("=" * 80)

    # Find a job that was updated by backfill
    cursor = db[Collections.JOBS].find({
        "$or": [
            {"salary_min": {"$exists": True, "$ne": None}},
            {"compensation_text": {"$exists": True, "$ne": None}}
        ]
    }).limit(5)

    jobs = await cursor.to_list(length=5)

    print(f"\nFound {len(jobs)} jobs with compensation data in database\n")

    for i, job in enumerate(jobs, 1):
        print(f"\n{i}. {job.get('title', 'Unknown')[:60]}")
        print(f"   Company: {job.get('company', 'Unknown')}")
        print("-" * 80)

        print("DATABASE FIELDS:")
        print(f"  salary_min: {job.get('salary_min')}")
        print(f"  salary_max: {job.get('salary_max')}")
        print(f"  stipend_min: {job.get('stipend_min')}")
        print(f"  stipend_max: {job.get('stipend_max')}")
        print(f"  compensation_text: {job.get('compensation_text')}")
        print(f"  compensation_type: {job.get('compensation_type')}")
        print(f"  salary_disclosed: {job.get('salary_disclosed')}")

        # Simulate what _strip_for_list does
        print("\nSIMULATED API RESPONSE (what frontend receives):")

        # Copy the job dict
        api_job = {**job}
        api_job.pop("_id", None)
        api_job.pop("jd_text", None)

        print(f"  salary_min: {api_job.get('salary_min')}")
        print(f"  salary_max: {api_job.get('salary_max')}")
        print(f"  stipend_min: {api_job.get('stipend_min')}")
        print(f"  compensation_text: {api_job.get('compensation_text')}")
        print(f"  compensation_type: {api_job.get('compensation_type')}")

    client.close()

if __name__ == "__main__":
    asyncio.run(test_api_response())
