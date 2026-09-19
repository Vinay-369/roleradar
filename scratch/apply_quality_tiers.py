import asyncio
import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
sys.stdout.reconfigure(encoding="utf-8")

from motor.motor_asyncio import AsyncIOMotorClient
from collections import Counter
from app.modules.jobs.completeness import evaluate_opportunity_completeness, QualityTier

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]
    coll = db["jobs"]

    all_docs = await coll.find({}).to_list(length=None)
    print(f"Evaluating quality tiers for {len(all_docs)} documents...")

    tier_counts = Counter()
    primary_india = 0
    secondary_india = 0
    rejected_india = 0

    for d in all_docs:
        res = evaluate_opportunity_completeness(d)
        tier = res.quality_tier.value
        rej_reason = res.rejection_reason
        tier_counts[tier] += 1

        is_india = d.get("country") == "India"
        is_active = d.get("verification_status") == "VERIFIED_ACTIVE"
        is_live_ats = d.get("source") in ("smartrecruiters", "lever", "greenhouse")

        if is_india and is_active and is_live_ats:
            if tier == "PRIMARY":
                primary_india += 1
            elif tier == "SECONDARY":
                secondary_india += 1
            else:
                rejected_india += 1

        await coll.update_one(
            {"id": d["id"]},
            {"$set": {
                "quality_tier": tier,
                "completeness_status": res.source_completeness.value,
                "rejection_reason": rej_reason
            }}
        )

    print("All documents updated!")
    print(f"Overall Quality Tiers across DB: {tier_counts}")
    print(f"Live Active Indian Direct ATS Requisitions Breakdown:")
    print(f"  PRIMARY (High Confidence / Rich Documentation): {primary_india}")
    print(f"  SECONDARY (Good Opportunity / Actionable): {secondary_india}")
    print(f"  REJECTED (Insufficient / Stub): {rejected_india}")
    print(f"  Total Live Active Indian Direct ATS: {primary_india + secondary_india + rejected_india}")

if __name__ == "__main__":
    asyncio.run(main())
