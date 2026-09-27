"""
Simple backfill script to fix missing compensation data.
Run this with: cd backend && python ../scratch/run_backfill_simple.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

async def simple_backfill():
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core.config import get_settings
    from app.db.mongo import Collections
    from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text

    print("\n" + "="*80)
    print("COMPENSATION DATA BACKFILL - SIMPLE VERSION")
    print("="*80 + "\n")

    settings = get_settings()
    print(f"Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Get all jobs
    cursor = db[Collections.JOBS].find({})
    all_jobs = await cursor.to_list(length=None)

    print(f"Found {len(all_jobs)} jobs in database\n")

    updated = 0
    skipped = 0
    errors = 0

    for i, job in enumerate(all_jobs, 1):
        if i % 50 == 0:
            print(f"Processing job {i}/{len(all_jobs)}...")

        job_id = job.get("id")
        title = job.get("title", "Unknown")
        company = job.get("company", "Unknown")

        # Skip if already has compensation
        has_comp = (
            job.get("salary_min") is not None or
            job.get("salary_max") is not None or
            job.get("stipend_min") is not None or
            job.get("compensation_text") is not None
        )

        if has_comp:
            skipped += 1
            continue

        # Extract compensation
        try:
            is_internship = (
                job.get("job_type") == "internship" or
                job.get("opportunity_type") == "INTERNSHIP" or
                "intern" in title.lower()
            )

            jd_text = job.get("jd_text") or job.get("description") or ""
            raw_payload = job.get("raw_payload")

            comp = extract_compensation_from_payload_and_text(
                text=jd_text,
                raw_payload=raw_payload,
                is_internship=is_internship,
            )

            # Only update if we found something
            if comp.compensation_type in ["NUMERIC", "QUALITATIVE"]:
                update_fields = {
                    "compensation_type": comp.compensation_type,
                    "salary_disclosed": comp.salary_disclosed,
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

                updated += 1

                display = comp.compensation_text or f"₹{comp.salary_min or comp.stipend_min}"
                print(f"✓ Updated: {title[:45]} @ {company[:20]} → {display[:30]}")
            else:
                skipped += 1

        except Exception as e:
            errors += 1
            print(f"✗ Error: {title[:45]} @ {company[:20]} | {str(e)[:50]}")

    await client.close()

    print("\n" + "="*80)
    print("BACKFILL COMPLETE")
    print("="*80)
    print(f"Total jobs:         {len(all_jobs)}")
    print(f"Updated:            {updated}")
    print(f"Skipped:            {skipped}")
    print(f"Errors:             {errors}")
    print(f"\nCompensation coverage: {(updated + skipped) / len(all_jobs) * 100:.1f}%")
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(simple_backfill())
    except KeyboardInterrupt:
        print("\n\nBackfill interrupted by user")
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
