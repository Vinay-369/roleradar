import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def inspect():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]

    # 1. Distinct sources
    sources = await db.jobs.distinct("source")
    print("Distinct sources in db.jobs:", sources)

    # 2. Distinct companies for each source
    for src in sources:
        companies = await db.jobs.distinct("company", {"source": src})
        count = await db.jobs.count_documents({"source": src})
        active_count = await db.jobs.count_documents({"source": src, "verification_status": "VERIFIED_ACTIVE"})
        print(f"Source: {src} ({count} total, {active_count} active) -> Companies ({len(companies)}): {companies[:5]}")

    # 3. Check for any live opportunity where apply_url is missing, empty, or not direct
    live_sources = ["smartrecruiters", "lever", "greenhouse"]
    no_apply = await db.jobs.find({
        "source": {"$in": live_sources},
        "$or": [
            {"apply_url": None},
            {"apply_url": ""},
            {"apply_url": {"$regex": "^http://example.com"}},
            {"is_direct_apply": {"$ne": True}}
        ]
    }).to_list(length=50)

    print(f"\nLive jobs without valid apply_url or is_direct_apply != True: {len(no_apply)}")
    for j in no_apply[:10]:
        print(f"  [{j.get('source')}] {j.get('id')} - {j.get('company')} - {j.get('title')}")
        print(f"     apply_url: {j.get('apply_url')}, is_direct_apply: {j.get('is_direct_apply')}")

    # 4. Check API route output for jobs: What does /api/matches/recommended return?
    # Let's check a sample of 20 jobs from the search_jobs query
    from app.modules.jobs import services as jobs_services
    sample_jobs = await jobs_services.search_jobs(db, {
        "skip": 0,
        "limit": 20,
        "active_discovery_only": True,
        "direct_apply_only": True,
        "include_benchmarks": False,
        "job_type": "full_time",
    })
    print(f"\nSample search_jobs (active_discovery_only, limit 20): {len(sample_jobs)}")
    for sj in sample_jobs[:5]:
        print(f"  {sj.get('id')} | {sj.get('company')} | {sj.get('title')}")
        print(f"     apply_url: {sj.get('apply_url')} | is_direct: {sj.get('is_direct_apply')} | status: {sj.get('verification_status')}")

if __name__ == "__main__":
    asyncio.run(inspect())
