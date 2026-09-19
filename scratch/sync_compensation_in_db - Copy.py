import asyncio
import sys

sys.path.insert(0, "backend")

from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection
from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text

async def main():
    await connect_to_mongo()
    db = get_db()
    try:
        query = {
            "verification_status": "VERIFIED_ACTIVE",
            "country": "India",
            "source": {"$in": ["smartrecruiters", "lever", "greenhouse"]}
        }
        cursor = db.jobs.find(query)
        total = 0
        updated = 0
        async for job in cursor:
            total += 1
            text = f"{job.get('description') or ''} {job.get('raw_html') or ''}"
            is_intern = (
                job.get("opportunity_type") == "INTERNSHIP"
                or job.get("job_type") == "internship"
                or "intern" in (job.get("title") or "").lower()
            )
            comp = extract_compensation_from_payload_and_text(
                text=text,
                raw_payload=job.get("raw_payload") or {},
                is_internship=is_intern
            )
            update_fields = {
                "compensation_type": comp.compensation_type,
                "compensation_text": comp.compensation_text,
            }
            if comp.salary_min is not None:
                update_fields["salary_min"] = comp.salary_min
            if comp.salary_max is not None:
                update_fields["salary_max"] = comp.salary_max
            if comp.stipend_min is not None:
                update_fields["stipend_min"] = comp.stipend_min
            if comp.salary_disclosed:
                update_fields["salary_disclosed"] = True

            await db.jobs.update_one({"_id": job["_id"]}, {"$set": update_fields})
            updated += 1

        print(f"Processed {total} live Indian opportunities. Updated {updated} in MongoDB.")
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
