"""
JobProvider implementations. CuratedJobProvider reads from MongoDB
after the curated seed dataset has been loaded — matching logic always
goes through this abstraction, never queries the jobs collection
directly, so a live external API can be added later as a second
provider without touching matching/recommendation code.
"""
from typing import Protocol

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.jobs import repositories as repo


class JobProvider(Protocol):
    async def search(self, filters: dict) -> list[dict]:
        ...


class CuratedJobProvider:
    """Reads curated/seeded jobs from MongoDB. Every job it returns
    carries source="curated" — RoleRadar never presents these as live
    listings without disclosing their source (Feature 8)."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db

    async def search(self, filters: dict) -> list[dict]:
        mongo_filter: dict = {}

        if filters.get("job_type"):
            mongo_filter["job_type"] = filters["job_type"]
        if filters.get("location"):
            mongo_filter["location"] = filters["location"]
        if filters.get("remote_only"):
            mongo_filter["is_remote"] = True
        if filters.get("fresher_friendly_only"):
            mongo_filter["fresher_friendly"] = True
        if filters.get("skill"):
            mongo_filter["skills_required"] = {"$regex": filters["skill"], "$options": "i"}
        if filters.get("min_lpa") is not None:
            mongo_filter["$or"] = [
                {"salary_disclosed": False},
                {"salary_max": {"$gte": filters["min_lpa"]}},
            ]

        return await repo.find_jobs(self._db, mongo_filter, limit=filters.get("limit", 100))
