"""
Diagnose missing salary and stipend data in jobs and internships.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections

async def diagnose_compensation():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    # Get all jobs
    jobs_cursor = db[Collections.JOBS].find({})
    all_jobs = await jobs_cursor.to_list(length=None)

    print(f"\n=== COMPENSATION DIAGNOSIS ===")
    print(f"Total jobs: {len(all_jobs)}")

    # Categorize by job type
    full_time_jobs = [j for j in all_jobs if j.get("job_type") != "internship"]
    internships = [j for j in all_jobs if j.get("job_type") == "internship"]

    print(f"\nFull-time jobs: {len(full_time_jobs)}")
    print(f"Internships: {len(internships)}")

    # Analyze full-time jobs
    ft_with_salary = [j for j in full_time_jobs if j.get("salary_min") or j.get("salary_max")]
    ft_with_compensation_text = [j for j in full_time_jobs if j.get("compensation_text")]
    ft_salary_disclosed = [j for j in full_time_jobs if j.get("salary_disclosed")]
    ft_no_compensation = [j for j in full_time_jobs if not (j.get("salary_min") or j.get("salary_max") or j.get("compensation_text"))]

    print(f"\n--- Full-Time Jobs ---")
    print(f"With salary_min/max: {len(ft_with_salary)} ({len(ft_with_salary)/len(full_time_jobs)*100:.1f}%)")
    print(f"With compensation_text: {len(ft_with_compensation_text)} ({len(ft_with_compensation_text)/len(full_time_jobs)*100:.1f}%)")
    print(f"Salary disclosed flag: {len(ft_salary_disclosed)} ({len(ft_salary_disclosed)/len(full_time_jobs)*100:.1f}%)")
    print(f"No compensation data: {len(ft_no_compensation)} ({len(ft_no_compensation)/len(full_time_jobs)*100:.1f}%)")

    # Analyze internships
    int_with_stipend = [j for j in internships if j.get("stipend_min") or j.get("stipend_max") or j.get("stipend")]
    int_with_compensation_text = [j for j in internships if j.get("compensation_text")]
    int_salary_disclosed = [j for j in internships if j.get("salary_disclosed")]
    int_no_compensation = [j for j in internships if not (j.get("stipend_min") or j.get("stipend_max") or j.get("stipend") or j.get("compensation_text"))]

    print(f"\n--- Internships ---")
    print(f"With stipend data: {len(int_with_stipend)} ({len(int_with_stipend)/len(internships)*100:.1f}% if internships else 0)")
    print(f"With compensation_text: {len(int_with_compensation_text)} ({len(int_with_compensation_text)/len(internships)*100:.1f}% if internships else 0)")
    print(f"Salary disclosed flag: {len(int_salary_disclosed)} ({len(int_salary_disclosed)/len(internships)*100:.1f}% if internships else 0)")
    print(f"No compensation data: {len(int_no_compensation)} ({len(int_no_compensation)/len(internships)*100:.1f}% if internships else 0)")

    # Show examples of missing compensation
    print(f"\n--- Sample Jobs Without Compensation (up to 10) ---")
    for i, job in enumerate(ft_no_compensation[:10]):
        print(f"\n{i+1}. {job.get('title')} at {job.get('company')}")
        print(f"   Source: {job.get('source')}")
        print(f"   JD snippet: {(job.get('jd_text') or job.get('description') or '')[:200]}...")

        # Check if raw payload has compensation
        if job.get("raw_payload"):
            payload = job.get("raw_payload")
            has_salary_range = payload.get("salaryRange")
            has_pay = payload.get("pay")
            has_compensation = payload.get("compensation")
            print(f"   Payload has salaryRange: {bool(has_salary_range)}")
            print(f"   Payload has pay: {bool(has_pay)}")
            print(f"   Payload has compensation: {bool(has_compensation)}")

    print(f"\n--- Sample Internships Without Compensation (up to 5) ---")
    for i, job in enumerate(int_no_compensation[:5]):
        print(f"\n{i+1}. {job.get('title')} at {job.get('company')}")
        print(f"   Source: {job.get('source')}")
        print(f"   JD snippet: {(job.get('jd_text') or job.get('description') or '')[:200]}...")

    await client.close()

if __name__ == "__main__":
    asyncio.run(diagnose_compensation())
