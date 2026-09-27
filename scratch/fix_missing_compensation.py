"""
Fix missing compensation data by re-extracting from raw payloads and JD text.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text

async def fix_compensation():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    # Get all jobs
    jobs_cursor = db[Collections.JOBS].find({})
    all_jobs = await jobs_cursor.to_list(length=None)

    print(f"\n=== COMPENSATION FIX ===")
    print(f"Total jobs in database: {len(all_jobs)}")

    updated_count = 0
    no_change_count = 0
    error_count = 0

    for job in all_jobs:
        job_id = job.get("id")
        title = job.get("title", "Unknown")
        company = job.get("company", "Unknown")
        is_internship = job.get("job_type") == "internship"

        # Get current compensation state
        has_salary = bool(job.get("salary_min") or job.get("salary_max"))
        has_stipend = bool(job.get("stipend_min") or job.get("stipend_max") or job.get("stipend"))
        has_comp_text = bool(job.get("compensation_text"))
        has_any_compensation = has_salary or has_stipend or has_comp_text

        # Skip if already has compensation
        if has_any_compensation:
            no_change_count += 1
            continue

        # Try to extract compensation
        try:
            jd_text = job.get("jd_text") or job.get("description") or ""
            raw_payload = job.get("raw_payload")

            comp = extract_compensation_from_payload_and_text(
                text=jd_text,
                raw_payload=raw_payload,
                is_internship=is_internship,
            )

            # Check if extraction found anything
            found_compensation = (
                comp.salary_min is not None or
                comp.salary_max is not None or
                comp.stipend_min is not None or
                comp.stipend_max is not None or
                comp.compensation_text is not None
            )

            if found_compensation:
                # Update the job
                update_fields = {
                    "salary_disclosed": comp.salary_disclosed,
                    "compensation_type": comp.compensation_type,
                }

                if comp.salary_min is not None:
                    update_fields["salary_min"] = comp.salary_min
                if comp.salary_max is not None:
                    update_fields["salary_max"] = comp.salary_max
                if comp.salary_currency is not None:
                    update_fields["salary_currency"] = comp.salary_currency
                if comp.stipend_min is not None:
                    update_fields["stipend_min"] = comp.stipend_min
                if comp.stipend_max is not None:
                    update_fields["stipend_max"] = comp.stipend_max
                if comp.compensation_text is not None:
                    update_fields["compensation_text"] = comp.compensation_text

                await db[Collections.JOBS].update_one(
                    {"id": job_id},
                    {"$set": update_fields}
                )

                updated_count += 1
                print(f"✓ Updated: {title} at {company}")
                print(f"  → {comp.compensation_type}: {comp.compensation_text or f'₹{comp.salary_min or comp.stipend_min}'}")
            else:
                no_change_count += 1

        except Exception as e:
            error_count += 1
            print(f"✗ Error processing {title} at {company}: {e}")

    print(f"\n=== SUMMARY ===")
    print(f"Total jobs: {len(all_jobs)}")
    print(f"Updated: {updated_count}")
    print(f"No change needed: {no_change_count}")
    print(f"Errors: {error_count}")

    await client.close()

if __name__ == "__main__":
    asyncio.run(fix_compensation())
