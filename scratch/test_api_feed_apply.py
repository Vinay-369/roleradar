import asyncio
import sys
sys.path.insert(0, "backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.modules.jobs import services as jobs_services
from app.modules.matching import services as matching_services
from app.modules.matching.routes import recommended_matches
from app.core.config import get_settings

async def test_api_feed():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]
    settings = get_settings()

    # Query recommended matches without resume (pre-resume discovery)
    feed_with_benchmarks = await recommended_matches(
        job_type="full_time",
        include_benchmarks=True,
        region="india",
        page=1,
        page_size=100,
        current_user={"_id": "test_user"},
        db=db,
        settings=settings,
    )

    print(f"Feed with benchmarks count: {len(feed_with_benchmarks)}")
    
    no_apply_live = []
    has_apply_live = []
    benchmarks = []

    for item in feed_with_benchmarks:
        m = item.model_dump()
        is_bm = m.get("source") == "curated_benchmark" or m.get("verification_status") == "MARKET_BENCHMARK"
        if is_bm:
            benchmarks.append(m)
        else:
            if not m.get("apply_url") or not m.get("is_direct_apply"):
                no_apply_live.append(m)
            else:
                has_apply_live.append(m)

    print(f"Benchmarks: {len(benchmarks)}")
    print(f"Live with Apply: {len(has_apply_live)}")
    print(f"Live WITHOUT Apply: {len(no_apply_live)}")

    for m in no_apply_live:
        print(f"  NO APPLY: [{m.get('source')}] {m.get('job_id')} - {m.get('company')} - {m.get('job_title')}")
        print(f"     apply_url: {repr(m.get('apply_url'))}")
        print(f"     is_direct_apply: {m.get('is_direct_apply')}, status: {m.get('verification_status')}, url_type: {m.get('url_type')}")

if __name__ == "__main__":
    asyncio.run(test_api_feed())
