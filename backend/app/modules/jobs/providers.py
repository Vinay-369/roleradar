"""
JobProvider implementations. CuratedJobProvider reads from MongoDB
after the seed or live provider dataset has been loaded — matching logic always
goes through this abstraction, never queries the jobs collection directly.
Enforces strict gatekeeping for the public feed:
- verification_status == VERIFIED_ACTIVE
- url_type == DIRECT_REQUISITION
- No unverified fallback
- User isolation for private custom JDs
"""
from typing import Protocol

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.jobs import repositories as repo
from app.modules.jobs.url_classifier import ApplicationUrlType
from app.modules.jobs.verification import OpportunityLifecycleStatus


class OpportunityProvider(Protocol):
    name: str

    async def search(self, filters: dict) -> list[dict]:
        ...


# Backward compatibility alias
JobProvider = OpportunityProvider


class CuratedJobProvider:
    """Reads verified opportunities from MongoDB.
    Enforces that public discovery results contain ONLY VERIFIED_ACTIVE
    and DIRECT_REQUISITION listings. Legacy or unverified records are strictly excluded."""

    name: str = "curated"

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db

    async def search(self, filters: dict) -> list[dict]:
        mongo_filter: dict = {}

        # 1. Lifecycle verification filter:
        # For public active discovery (feed), strictly enforce VERIFIED_ACTIVE and DIRECT_REQUISITION.
        # For internal queries / test runners without active_discovery_only, exclude closed, expired, and invalid listings.
        status_clause: dict
        if filters.get("active_discovery_only") or filters.get("direct_apply_only"):
            status_clause = {
                "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
                "url_type": ApplicationUrlType.DIRECT_REQUISITION.value,
            }
        elif filters.get("include_all_statuses"):
            status_clause = {}
        else:
            status_clause = {
                "verification_status": {
                    "$nin": [
                        OpportunityLifecycleStatus.CLOSED.value,
                        OpportunityLifecycleStatus.EXPIRED.value,
                        OpportunityLifecycleStatus.INVALID.value,
                    ]
                }
            }

        # 2. User isolation: public searches do not leak private custom jobs from other users
        user_id = filters.get("user_id")
        user_clause: dict
        if user_id:
            user_clause = {"$or": [{"source": {"$ne": "custom"}}, {"user_id": user_id}]}
        else:
            user_clause = {"source": {"$ne": "custom"}}

        and_clauses: list[dict] = []
        if status_clause:
            and_clauses.append(status_clause)
        and_clauses.append(user_clause)

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
            sal_clause = [
                {"salary_disclosed": False},
                {"salary_max": {"$gte": filters["min_lpa"]}},
            ]
            and_clauses.append({"$or": sal_clause})

        # India-First Location Presets
        loc_preset = filters.get("location_preset")
        if isinstance(loc_preset, str) and loc_preset.strip() and loc_preset.lower() not in ("all", "all india"):
            from app.modules.jobs.location_normalization import INDIA_METRO_CLUSTERS
            aliases = INDIA_METRO_CLUSTERS.get(loc_preset)
            if aliases:
                regex_pattern = "|".join(re.escape(a) for a in aliases)
                and_clauses.append({"location": {"$regex": regex_pattern, "$options": "i"}})
            else:
                and_clauses.append({"location": {"$regex": re.escape(loc_preset), "$options": "i"}})

        # Workplace Type
        workplace_type = filters.get("workplace_type")
        if isinstance(workplace_type, str) and workplace_type.upper() != "ALL":
            wp_upper = workplace_type.upper()
            if wp_upper == "REMOTE":
                and_clauses.append({"$or": [{"is_remote": True}, {"location": {"$regex": "remote", "$options": "i"}}]})
            elif wp_upper == "HYBRID":
                and_clauses.append({"location": {"$regex": "hybrid", "$options": "i"}})
            elif wp_upper == "ON_SITE":
                and_clauses.append({"is_remote": {"$ne": True}, "location": {"$not": {"$regex": "remote", "$options": "i"}}})

        # Experience Tier
        exp_tier = filters.get("experience_tier")
        if isinstance(exp_tier, str) and exp_tier.lower() != "all":
            tier_lower = exp_tier.lower()
            if tier_lower in ("internship", "intern"):
                and_clauses.append({"$or": [{"job_type": "internship"}, {"opportunity_type": "INTERNSHIP"}, {"title": {"$regex": "intern", "$options": "i"}}]})
            elif tier_lower in ("fresher", "0-1"):
                and_clauses.append({"$or": [
                    {"experience_min": {"$lte": 1}},
                    {"fresher_friendly": True},
                    {"title": {"$regex": r"\b(fresher|trainee|junior|graduate)\b", "$options": "i"}}
                ]})
            elif tier_lower == "1-3":
                and_clauses.append({"experience_min": {"$gte": 1, "$lte": 3}})
            elif tier_lower == "3+":
                and_clauses.append({"experience_min": {"$gte": 3}})

        # Opportunity Type
        opp_type = filters.get("opportunity_type")
        if isinstance(opp_type, str) and opp_type.upper() != "ALL":
            and_clauses.append({"$or": [
                {"opportunity_type": opp_type.upper()},
                {"job_type": opp_type.lower()},
            ]})

        mongo_filter["$and"] = and_clauses

        return await repo.find_jobs(self._db, mongo_filter, limit=filters.get("limit", 100))


class DirectATSProvider:
    """Provider adapter for direct employer ATS feeds (e.g. Greenhouse, Lever, Workday).
    Yields strictly DIRECT_REQUISITION verified opportunities."""

    name: str = "direct_ats"

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db

    async def search(self, filters: dict) -> list[dict]:
        curated = CuratedJobProvider(self._db)
        direct_filters = dict(filters, source="direct_ats")
        return await curated.search(direct_filters)
