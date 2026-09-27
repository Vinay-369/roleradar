"""
Backfill missing compensation data for all jobs and internships.
Re-extracts compensation from raw_payload and jd_text for jobs that are missing it.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text

async def backfill_compensation():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    # Get all jobs
    jobs_cursor = db[Collections.JOBS].find({})
    all_jobs = await jobs_cursor.to_list(length=None)

    print(f"\n{'='*60}")
    print(f"COMPENSATION DATA BACKFILL")
    print(f"{'='*60}")
    print(f"Total jobs in database: {len(all_jobs)}\n")

    # Categorize jobs
    full_time_jobs = [j for j in all_jobs if j.get("job_type") != "internship"]
    internships = [j for j in all_jobs if j.get("job_type") == "internship"]

    print(f"Full-time jobs: {len(full_time_jobs)}")
    print(f"Internships: {len(internships)}\n")

    stats = {
        "total_processed": 0,
        "already_had_data": 0,
        "newly_extracted_numeric": 0,
        "newly_extracted_qualitative": 0,
        "still_undisclosed": 0,
        "errors": 0
    }

    for job in all_jobs:
        stats["total_processed"] += 1
        job_id = job.get("id")
        title = job.get("title", "Unknown")
        company = job.get("company", "Unknown")
        source = job.get("source", "unknown")
        is_internship = job.get("job_type") == "internship"

        # Check current compensation state
        has_salary = bool(job.get("salary_min") or job.get("salary_max"))
        has_stipend = bool(job.get("stipend_min") or job.get("stipend_max") or job.get("stipend"))
        has_comp_text = bool(job.get("compensation_text"))
        compensation_type = job.get("compensation_type", "UNDISCLOSED")

        # Skip if already has numeric or qualitative compensation
        if compensation_type in ["NUMERIC", "QUALITATIVE"]:
            stats["already_had_data"] += 1
            continue

        # Extract compensation
        try:
            jd_text = job.get("jd_text") or job.get("description") or ""
            raw_payload = job.get("raw_payload")

            comp = extract_compensation_from_payload_and_text(
                text=jd_text,
                raw_payload=raw_payload,
                is_internship=is_internship,
            )

            # Check if extraction found anything new
            if comp.compensation_type == "NUMERIC":
                # Build update fields
                update_fields = {
                    "salary_disclosed": True,
                    "compensation_type": "NUMERIC",
                }

                if comp.salary_min is not None:
                    update_fields["salary_min"] = comp.salary_min
                if comp.salary_max is not None:
                    update_fields["salary_max"] = comp.salary_max
                if comp.salary_currency:
                    update_fields["salary_currency"] = comp.salary_currency
                if comp.stipend_min is not None:
                    update_fields["stipend_min"] = comp.stipend_min
                if comp.stipend_max is not None:
                    update_fields["stipend_max"] = comp.stipend_max
                if comp.compensation_text:
                    update_fields["compensation_text"] = comp.compensation_text

                await db[Collections.JOBS].update_one(
                    {"id": job_id},
                    {"$set": update_fields}
                )

                stats["newly_extracted_numeric"] += 1
                comp_display = comp.compensation_text or f"₹{comp.salary_min or comp.stipend_min}"
                print(f"✓ NUMERIC: {title[:40]} @ {company[:20]} | {comp_display}")

            elif comp.compensation_type == "QUALITATIVE":
                update_fields = {
                    "salary_disclosed": True,
                    "compensation_type": "QUALITATIVE",
                    "compensation_text": comp.compensation_text,
                }

                await db[Collections.JOBS].update_one(
                    {"id": job_id},
                    {"$set": update_fields}
                )

                stats["newly_extracted_qualitative"] += 1
                print(f"✓ QUALITATIVE: {title[:40]} @ {company[:20]} | {comp.compensation_text}")

            else:
                # Still undisclosed
                stats["still_undisclosed"] += 1

        except Exception as e:
            stats["errors"] += 1
            print(f"✗ ERROR: {title[:40]} @ {company[:20]} | {str(e)[:50]}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"BACKFILL SUMMARY")
    print(f"{'='*60}")
    print(f"Total processed:           {stats['total_processed']}")
    print(f"Already had data:          {stats['already_had_data']}")
    print(f"Newly extracted (numeric): {stats['newly_extracted_numeric']}")
    print(f"Newly extracted (qual):    {stats['newly_extracted_qualitative']}")
    print(f"Still undisclosed:         {stats['still_undisclosed']}")
    print(f"Errors:                    {stats['errors']}")
    print(f"\nTotal with compensation:   {stats['already_had_data'] + stats['newly_extracted_numeric'] + stats['newly_extracted_qualitative']}")
    print(f"Coverage: {(stats['already_had_data'] + stats['newly_extracted_numeric'] + stats['newly_extracted_qualitative']) / stats['total_processed'] * 100:.1f}%")

    await client.close()

if __name__ == "__main__":
    asyncio.run(backfill_compensation())
