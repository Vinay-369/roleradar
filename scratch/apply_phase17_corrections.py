import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.learning.role_taxonomy import resolve_role
from app.modules.jobs.location_normalization import is_india_opportunity

async def main():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    coll = db[Collections.JOBS]

    cursor = coll.find({"verification_status": "VERIFIED_ACTIVE"})
    all_active = await cursor.to_list(10000)
    
    indian_active = [
        o for o in all_active
        if o.get("country") == "India" or is_india_opportunity(o.get("location", ""), o.get("description", ""))
    ]
    print(f"Total live active Indian docs in DB: {len(indian_active)}")

    updated_count = 0
    remapped_from_sr = 0
    remapped_details = []

    for doc in indian_active:
        title = doc.get("title", "")
        old_role = doc.get("canonical_role", "")
        
        profile, conf, key = resolve_role(title)
        if profile:
            new_role = profile.canonical_role
            new_key = key
            new_domain = profile.domain
        else:
            new_role = "Specialized Requisition"
            new_key = "specialized_requisition"
            new_domain = "Specialized Operations"
            
        if old_role != new_role:
            if old_role == "Specialized Requisition":
                remapped_from_sr += 1
                remapped_details.append({
                    "company": doc.get("company"),
                    "title": title,
                    "old_role": old_role,
                    "new_role": new_role,
                    "domain": new_domain
                })
            await coll.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    "canonical_role": new_role,
                    "canonical_role_key": new_key,
                    "role_domain": new_domain
                }}
            )
            updated_count += 1

    print(f"\nCompleted MongoDB update:")
    print(f"  Total updated: {updated_count}")
    print(f"  Remapped from Specialized Requisition: {remapped_from_sr}")
    for item in remapped_details:
        print(f"    [{item['company']}] '{item['title']}' -> {item['new_role']} ({item['domain']})")

    # Verify new Specialized Requisition count among unique active Indian
    unique_active_in = []
    for doc in indian_active:
        # deduplicate gh_inmobi_8138503
        if doc.get("external_id") == "gh_inmobi_8138503" or doc.get("id") == "gh_inmobi_8138503":
            continue
        unique_active_in.append(doc)

    print(f"\nUnique active Indian count: {len(unique_active_in)}")
    # Reload from db to verify stored values
    cursor_recheck = coll.find({"verification_status": "VERIFIED_ACTIVE"})
    all_recheck = await cursor_recheck.to_list(10000)
    in_recheck = [
        o for o in all_recheck
        if (o.get("country") == "India" or is_india_opportunity(o.get("location", ""), o.get("description", "")))
        and o.get("external_id") != "gh_inmobi_8138503" and o.get("id") != "gh_inmobi_8138503"
    ]
    sr_count = sum(1 for d in in_recheck if d.get("canonical_role") == "Specialized Requisition")
    print(f"Stored Specialized Requisition count in DB: {sr_count} (was 383)")

if __name__ == "__main__":
    asyncio.run(main())
