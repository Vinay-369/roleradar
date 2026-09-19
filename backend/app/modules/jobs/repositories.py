from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import Collections


async def count_jobs(db: AsyncIOMotorDatabase) -> int:
    return await db[Collections.JOBS].count_documents({})


async def bulk_insert_jobs(db: AsyncIOMotorDatabase, jobs: list[dict]) -> None:
    if not jobs:
        return
    await db[Collections.JOBS].delete_many({"source": "curated"})
    await db[Collections.JOBS].insert_many(jobs)


async def upsert_jobs(db: AsyncIOMotorDatabase, jobs: list[dict]) -> None:
    """Insert-or-update by the job's own `id` field (not Mongo's _id) --
    used for live-fetched jobs so repeated searches refresh existing
    entries instead of duplicating them."""
    for job in jobs:
        await db[Collections.JOBS].update_one({"id": job["id"]}, {"$set": job}, upsert=True)


async def find_jobs(
    db: AsyncIOMotorDatabase,
    mongo_filter: dict,
    limit: int = 100,
    skip: int = 0,
    sort: list[tuple[str, int]] | None = None,
) -> list[dict]:
    cursor = db[Collections.JOBS].find(mongo_filter)
    if sort:
        cursor = cursor.sort(sort)
    if skip > 0:
        cursor = cursor.skip(skip)
    cursor = cursor.limit(limit)
    return await cursor.to_list(length=limit)


async def count_filtered_jobs(db: AsyncIOMotorDatabase, mongo_filter: dict) -> int:
    import inspect
    coll = db[Collections.JOBS]
    count_fn = getattr(coll, "count_documents", None)
    if count_fn is not None:
        res = count_fn(mongo_filter)
        if inspect.isawaitable(res):
            return await res
        if isinstance(res, (int, float)):
            return int(res)
    return 0


async def get_job_by_id(db: AsyncIOMotorDatabase, job_id: str) -> dict | None:
    job = await db[Collections.JOBS].find_one({"id": job_id})
    if not job:
        from bson import ObjectId
        if ObjectId.is_valid(job_id):
            job = await db[Collections.JOBS].find_one({"_id": ObjectId(job_id)})
        if not job:
            job = await db[Collections.JOBS].find_one({"_id": job_id})
    return job
