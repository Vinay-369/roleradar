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

    def _build_mongo_query(self, filters: dict) -> dict:
        mongo_filter: dict = {}

        # 1. Lifecycle verification status
        status_clause: dict
        if filters.get("include_all_statuses"):
            status_clause = {}
        elif filters.get("include_benchmarks"):
            status_clause = {
                "verification_status": {
                    "$in": [
                        OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
                        OpportunityLifecycleStatus.MARKET_BENCHMARK.value,
                    ]
                }
            }
        elif filters.get("active_discovery_only") or filters.get("direct_apply_only"):
            status_clause = {
                "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
                "url_type": ApplicationUrlType.DIRECT_REQUISITION.value,
            }
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

        and_clauses: list[dict] = [status_clause] if status_clause else []

        # 2. Completeness Quality: Exclude INSUFFICIENT records from primary recommendations
        if not filters.get("include_insufficient"):
            and_clauses.append({"completeness_status": {"$ne": "INSUFFICIENT"}})

        # 3. User isolation
        user_id = filters.get("user_id")
        user_clause = {"$or": [{"source": {"$ne": "custom"}}, {"user_id": user_id}]} if user_id else {"source": {"$ne": "custom"}}
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

        # Canonical Role Filter
        role_filter = filters.get("role")
        if isinstance(role_filter, str) and role_filter.strip() and role_filter.upper() != "ALL":
            import re
            from app.modules.learning.role_taxonomy import resolve_role
            target_prof, _, _ = resolve_role(role_filter)
            if target_prof:
                all_names = [target_prof.canonical_role] + list(target_prof.aliases)
                alias_pattern = "|".join(re.escape(a) for a in all_names)
                and_clauses.append({"$or": [
                    {"canonical_role": target_prof.canonical_role},
                    {"canonical_role_key": target_prof.canonical_role.lower().replace(" ", "_")},
                    {"title": {"$regex": f"\\b({alias_pattern})\\b", "$options": "i"}},
                ]})
            else:
                and_clauses.append({"title": {"$regex": re.escape(role_filter), "$options": "i"}})

        # Domain Filter
        domain_filter = filters.get("domain")
        if isinstance(domain_filter, str) and domain_filter.strip() and domain_filter.upper() != "ALL":
            import re
            and_clauses.append({"$or": [
                {"role_domain": {"$regex": re.escape(domain_filter), "$options": "i"}},
                {"industry": {"$regex": re.escape(domain_filter), "$options": "i"}},
            ]})

        # Freshness / Days Posted Max
        max_days = filters.get("max_posted_days")
        if max_days is not None:
            try:
                m_int = int(max_days)
                if m_int > 0:
                    and_clauses.append({"posted_days_ago": {"$lte": m_int}})
            except (ValueError, TypeError):
                pass

        # India-First Location Presets
        loc_preset = filters.get("location_preset")
        if isinstance(loc_preset, str) and loc_preset.strip() and loc_preset.lower() not in ("all", "all india"):
            import re
            from app.modules.jobs.location_normalization import INDIA_METRO_CLUSTERS
            aliases = INDIA_METRO_CLUSTERS.get(loc_preset)
            if aliases:
                regex_pattern = "|".join(re.escape(a) for a in aliases)
                and_clauses.append({"location": {"$regex": regex_pattern, "$options": "i"}})
            else:
                and_clauses.append({"location": {"$regex": re.escape(loc_preset), "$options": "i"}})

        # Regional Scope Filter
        region_filter = filters.get("region")
        if isinstance(region_filter, str) and region_filter.strip() and region_filter.lower() in ("india", "in"):
            and_clauses.append({
                "$or": [
                    {"country": "India"},
                    {"location": {"$regex": r"\b(india|bharat|bangalore|bengaluru|mumbai|delhi|gurgaon|gurugram|noida|hyderabad|pune|chennai|kolkata|ahmedabad|chandigarh|jaipur|indore|kochi|coimbatore|vadodara|lucknow|nagpur|bhubaneswar|thiruvananthapuram)\b", "$options": "i"}}
                ]
            })

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

        # Canonical Registration Career Stage
        stage = filters.get("stage")
        if isinstance(stage, str) and stage.strip() and stage.upper() != "ALL":
            st_upper = stage.upper().strip()
            if st_upper == "FRESHER":
                and_clauses.append({"$or": [
                    {"experience_min": {"$lte": 1}},
                    {"fresher_friendly": True},
                    {"fresher_eligible": True},
                    {"candidate_suitability": "FRESHER"},
                    {"title": {"$regex": r"\b(fresher|trainee|junior|graduate|entry|intern)\b", "$options": "i"}},
                ]})
            elif st_upper == "INTERNSHIP_SEEKER":
                and_clauses.append({"$or": [
                    {"job_type": "internship"},
                    {"opportunity_type": "INTERNSHIP"},
                    {"student_eligible": True},
                    {"candidate_suitability": "STUDENT"},
                    {"title": {"$regex": "intern", "$options": "i"}},
                ]})
            elif st_upper == "EXPERIENCED":
                and_clauses.append({"$or": [
                    {"experience_min": {"$gte": 1}},
                    {"candidate_suitability": {"$in": ["EXPERIENCED", "MID_LEVEL", "SENIOR"]}},
                    {"title": {"$regex": r"\b(senior|lead|experienced|staff|principal|ii|iii|mid)\b", "$options": "i"}},
                ]})
            elif st_upper == "CAREER_SWITCHER":
                and_clauses.append({"$or": [
                    {"experience_min": {"$lte": 3}},
                    {"fresher_friendly": True},
                    {"candidate_suitability": {"$in": ["EARLY_CAREER", "FRESHER", "ASSOCIATE"]}},
                ]})

        # Keyword / Free Text Search
        search_q = filters.get("search") or filters.get("q")
        if isinstance(search_q, str) and search_q.strip():
            import re
            q_re = re.escape(search_q.strip())
            and_clauses.append({"$or": [
                {"title": {"$regex": q_re, "$options": "i"}},
                {"company": {"$regex": q_re, "$options": "i"}},
                {"skills_required": {"$regex": q_re, "$options": "i"}},
                {"location": {"$regex": q_re, "$options": "i"}},
            ]})

        # Legacy Experience Tier (maintained for backward compatibility)
        exp_tier = filters.get("experience_tier")
        if isinstance(exp_tier, str) and exp_tier.lower() != "all" and not stage:
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

        if and_clauses:
            mongo_filter["$and"] = and_clauses

        return mongo_filter

    async def search(self, filters: dict) -> list[dict]:
        mongo_filter = self._build_mongo_query(filters)

        skip = int(filters.get("skip", 0))
        limit = int(filters.get("limit", 100))

        sort_by = filters.get("sort_by", "recent")
        if sort_by == "salary":
            sort_spec = [("salary_max", -1), ("salary_min", -1), ("quality_tier", 1), ("completeness_status", 1), ("posted_days_ago", 1), ("id", 1)]
        elif sort_by == "stipend":
            sort_spec = [("stipend", -1), ("stipend_min", -1), ("quality_tier", 1), ("completeness_status", 1), ("posted_days_ago", 1), ("id", 1)]
        else:
            sort_spec = [("quality_tier", 1), ("completeness_status", 1), ("posted_days_ago", 1), ("id", 1)]

        return await repo.find_jobs(self._db, mongo_filter, limit=limit, skip=skip, sort=sort_spec)

    async def count(self, filters: dict) -> int:
        mongo_filter = self._build_mongo_query(filters)
        return await repo.count_filtered_jobs(self._db, mongo_filter)


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
