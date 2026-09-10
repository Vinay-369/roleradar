import asyncio
import json
import sys
sys.path.insert(0, ".")

from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]
    coll = db["jobs"]

    out = []
    cursor = coll.find({"title": {"$regex": "Full Stack", "$options": "i"}})
    docs = await cursor.to_list(length=30)
    for doc in docs:
        desc = doc.get("description", "")
        jd_count = desc.upper().count("JOB DESCRIPTION")
        qual_count = desc.upper().count("QUALIFICATION")
        out.append(f"ID: {doc.get('id')} | Company: {doc.get('company')} | Title: {doc.get('title')} | JD count: {jd_count} | Qual count: {qual_count}")
        if jd_count > 1 or qual_count > 1:
            out.append("--- REPEATED HEADINGS FOUND ---")
            out.append(repr(desc[:1200]))
            out.append("="*60)

    cursor2 = coll.find({"verification_status": "VERIFIED_ACTIVE"})
    all_active = await cursor2.to_list(length=None)
    repeated_jobs = []
    for doc in all_active:
        desc = doc.get("description", "")
        jd_count = desc.upper().count("JOB DESCRIPTION")
        qual_count = desc.upper().count("QUALIFICATION")
        if jd_count > 1 or qual_count > 1:
            repeated_jobs.append((doc.get("id"), doc.get("company"), doc.get("title"), jd_count, qual_count))

    out.append(f"\nTotal active jobs with repeated headings: {len(repeated_jobs)}")
    for r in repeated_jobs[:20]:
        out.append(f"  {r}")

    if repeated_jobs:
        sample_id = repeated_jobs[0][0]
        sample_doc = await coll.find_one({"id": sample_id})
        out.append(f"\nSample doc: {sample_id} full description:")
        out.append(str(sample_doc.get("description")))

    with open("scratch/repeated_headings_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("Wrote scratch/repeated_headings_results.txt")

if __name__ == "__main__":
    asyncio.run(main())
