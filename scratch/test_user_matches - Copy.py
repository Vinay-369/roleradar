import asyncio
import sys
sys.path.insert(0, "backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.modules.matching.routes import recommended_matches
from app.core.config import get_settings

async def test_all_cases():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]
    settings = get_settings()

    # Find a real user in the DB
    user = await db.users.find_one({})
    user_id = str(user["_id"]) if user else "test_user"
    print(f"Testing with user_id: {user_id}")

    # Check if this user has a resume
    resume = await db.resumes.find_one({"user_id": user_id, "is_master": True})
    print(f"User has master resume: {resume is not None}")

    # Test 1: recommended_matches with include_benchmarks=True
    res = await recommended_matches(
        job_type="full_time",
        include_benchmarks=True,
        region="india",
        page=1,
        page_size=100,
        current_user={"_id": user_id},
        db=db,
        settings=settings,
    )

    print(f"\nTotal returned from recommended_matches (with benchmarks): {len(res)}")
    for i, item in enumerate(res[:15]):
        m = item.model_dump()
        print(f"#{i+1}: [{m.get('source')}] {m.get('job_id')} - {m.get('company')} - {m.get('job_title')}")
        print(f"     apply_url: {repr(m.get('apply_url'))}")
        print(f"     is_direct_apply: {m.get('is_direct_apply')}, status: {m.get('verification_status')}")

    # Test 2: recommended_matches with include_benchmarks=False (Active discovery only)
    res_no_bm = await recommended_matches(
        job_type="full_time",
        include_benchmarks=False,
        region="india",
        page=1,
        page_size=100,
        current_user={"_id": user_id},
        db=db,
        settings=settings,
    )
    print(f"\nTotal returned (active only): {len(res_no_bm)}")
    missing_apply = [item for item in res_no_bm if not item.apply_url or not item.is_direct_apply]
    print(f"Missing apply among active: {len(missing_apply)}")
    for ma in missing_apply:
        print(f"  MISSING: [{ma.source}] {ma.job_id} - {ma.company} - {ma.job_title} | apply_url={repr(ma.apply_url)} | is_direct={ma.is_direct_apply}")

if __name__ == "__main__":
    asyncio.run(test_all_cases())
