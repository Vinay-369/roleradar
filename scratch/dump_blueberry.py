import asyncio
import json
import sys
sys.path.insert(0, ".")

from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]
    coll = db["jobs"]

    # 1. Blueberry Labs jobs
    out = []
    cursor = coll.find({"company": {"$regex": "Blueberry", "$options": "i"}})
    docs = await cursor.to_list(length=10)
    for doc in docs:
        out.append(f"=== ID: {doc.get('id')} | Title: {doc.get('title')} ===")
        out.append(f"responsibilities count: {len(doc.get('responsibilities', []))}")
        out.append(f"qualifications count: {len(doc.get('qualifications', []))}")
        desc = doc.get("description", "")
        out.append("DESCRIPTION:")
        out.append(desc)
        out.append("="*80)

    with open("scratch/blueberry_jobs.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("Wrote scratch/blueberry_jobs.txt")

if __name__ == "__main__":
    asyncio.run(main())
