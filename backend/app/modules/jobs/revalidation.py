"""
Scheduled Revalidation Engine.
Periodically audits opportunities stored in MongoDB:
- Evaluates freshness against immutable UTC timestamps (posted_at or first_seen_at)
- Transitions listings > MAX_FRESHNESS_DAYS (45d) to EXPIRED
- Evaluates provider closure signals and content markers -> transitions to CLOSED
- Evaluates staleness (> 14 days without audit) -> transitions to STALE
- Updates last_verified_at timestamp
- Excludes inactive records from active discovery feed
"""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import Collections
from app.modules.jobs.url_classifier import ApplicationUrlType, classify_application_url
from app.modules.jobs.verification import (
    MAX_FRESHNESS_DAYS,
    STALE_THRESHOLD_DAYS,
    OpportunityLifecycleStatus,
    verify_opportunity_sync,
)

logger = logging.getLogger(__name__)


async def revalidate_all_active_opportunities(
    db: AsyncIOMotorDatabase,
    now: datetime | None = None,
    max_freshness_days: int = MAX_FRESHNESS_DAYS,
) -> dict:
    """
    Audits all opportunities currently marked VERIFIED_ACTIVE in MongoDB.
    Updates their status and timestamps based on current verification rules.
    Returns audit statistics dictionary.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    cursor = db[Collections.JOBS].find({
        "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
    })
    active_jobs = await cursor.to_list(length=2000)

    stats = {
        "checked": len(active_jobs),
        "retained_active": 0,
        "transitioned_closed": 0,
        "transitioned_expired": 0,
        "transitioned_stale": 0,
        "transitioned_invalid": 0,
    }

    for job in active_jobs:
        # Re-evaluate verification
        vres = verify_opportunity_sync(job, now=now, enforce_direct_apply=True)
        new_status = vres.status.value

        update_fields = {
            "verification_status": new_status,
            "last_verified_at": now_iso,
            "verified_at": now_iso,
            "verification_reason": vres.reason,
            "verification_method": "revalidation_audit",
            "url_type": vres.url_type.value,
            "is_direct_apply": (vres.url_type == ApplicationUrlType.DIRECT_REQUISITION and new_status == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value),
        }

        if new_status == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value:
            stats["retained_active"] += 1
        elif new_status == OpportunityLifecycleStatus.CLOSED.value:
            stats["transitioned_closed"] += 1
        elif new_status == OpportunityLifecycleStatus.EXPIRED.value:
            stats["transitioned_expired"] += 1
        elif new_status == OpportunityLifecycleStatus.STALE.value:
            stats["transitioned_stale"] += 1
        elif new_status == OpportunityLifecycleStatus.INVALID.value:
            stats["transitioned_invalid"] += 1

        await db[Collections.JOBS].update_one({"id": job["id"]}, {"$set": update_fields})

    logger.info(
        f"Revalidation audit completed: {stats['checked']} audited, "
        f"{stats['retained_active']} retained active, "
        f"{stats['transitioned_closed']} closed, {stats['transitioned_expired']} expired."
    )
    return stats
