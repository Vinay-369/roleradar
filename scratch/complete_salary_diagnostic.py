"""
Complete diagnostic: Check database, API response, and frontend display logic.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

async def complete_diagnostic():
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core.config import get_settings
    from app.db.mongo import Collections
    from app.modules.jobs.routes import _strip_for_list

    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    print("=" * 80)
    print("SALARY VISIBILITY DIAGNOSTIC")
    print("=" * 80)

    # Get sample jobs
    cursor = db[Collections.JOBS].find({}).limit(20)
    jobs = await cursor.to_list(length=20)

    print(f"\nTotal jobs in sample: {len(jobs)}")

    # Check database state
    jobs_with_salary = [j for j in jobs if j.get("salary_min") or j.get("salary_max")]
    jobs_with_stipend = [j for j in jobs if j.get("stipend_min") or j.get("stipend_max") or j.get("stipend")]
    jobs_with_comp_text = [j for j in jobs if j.get("compensation_text")]
    jobs_with_any_comp = [j for j in jobs if j.get("salary_min") or j.get("salary_max") or j.get("stipend_min") or j.get("stipend_max") or j.get("stipend") or j.get("compensation_text")]

    print(f"\n--- DATABASE STATE ---")
    print(f"Jobs with salary_min/max: {len(jobs_with_salary)} ({len(jobs_with_salary)/len(jobs)*100:.1f}%)")
    print(f"Jobs with stipend data: {len(jobs_with_stipend)} ({len(jobs_with_stipend)/len(jobs)*100:.1f}%)")
    print(f"Jobs with compensation_text: {len(jobs_with_comp_text)} ({len(jobs_with_comp_text)/len(jobs)*100:.1f}%)")
    print(f"Jobs with ANY compensation: {len(jobs_with_any_comp)} ({len(jobs_with_any_comp)/len(jobs)*100:.1f}%)")

    # Detailed examples
    print(f"\n--- DETAILED EXAMPLES ---")

    for i, job in enumerate(jobs[:5], 1):
        print(f"\n{i}. {job.get('title', 'Unknown')[:45]} @ {job.get('company', 'Unknown')[:20]}")
        print(f"   Source: {job.get('source')}, Type: {job.get('job_type')}")

        # Database fields
        print(f"   DB - salary_min: {job.get('salary_min')}")
        print(f"   DB - salary_max: {job.get('salary_max')}")
        print(f"   DB - stipend_min: {job.get('stipend_min')}")
        print(f"   DB - compensation_text: {job.get('compensation_text')}")
        print(f"   DB - compensation_type: {job.get('compensation_type')}")

        # After API processing
        try:
            processed = _strip_for_list(dict(job))
            print(f"   API - salary_min: {processed.get('salary_min')}")
            print(f"   API - salary_max: {processed.get('salary_max')}")
            print(f"   API - stipend_min: {processed.get('stipend_min')}")
            print(f"   API - compensation_text: {processed.get('compensation_text')}")

            # What frontend would display
            if processed.get('salary_min') and processed.get('salary_max'):
                display = f"₹{processed.get('salary_min')}–{processed.get('salary_max')} LPA"
            elif processed.get('salary_min'):
                display = f"₹{processed.get('salary_min')}+ LPA"
            elif processed.get('stipend_min') and processed.get('stipend_max'):
                display = f"₹{processed.get('stipend_min'):,}–{processed.get('stipend_max'):,} / mo"
            elif processed.get('stipend_min'):
                display = f"₹{processed.get('stipend_min'):,} / mo"
            elif processed.get('compensation_text'):
                if 'best in industry' in processed.get('compensation_text', '').lower():
                    display = "Best in industry"
                elif 'commensurate' in processed.get('compensation_text', '').lower():
                    display = "Commensurate"
                else:
                    display = "Competitive"
            else:
                display = "NOT VISIBLE (no data)"

            print(f"   FRONTEND DISPLAY: {display}")
        except Exception as e:
            print(f"   API ERROR: {e}")

    # Check if compensation extraction is working
    print(f"\n--- TESTING COMPENSATION EXTRACTION ---")
    from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text

    test_job = jobs[0] if jobs else None
    if test_job:
        jd_text = test_job.get('jd_text') or test_job.get('description') or ''
        raw_payload = test_job.get('raw_payload')
        is_intern = test_job.get('job_type') == 'internship'

        comp = extract_compensation_from_payload_and_text(
            text=jd_text,
            raw_payload=raw_payload,
            is_internship=is_intern,
        )

        print(f"Test job: {test_job.get('title', 'Unknown')[:40]}")
        print(f"  Extraction result:")
        print(f"    Type: {comp.compensation_type}")
        print(f"    salary_min: {comp.salary_min}")
        print(f"    salary_max: {comp.salary_max}")
        print(f"    compensation_text: {comp.compensation_text}")

    await client.close()

if __name__ == "__main__":
    asyncio.run(complete_diagnostic())
