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
    print("--- BLUEBERRY LABS JOBS ---")
    cursor = coll.find({"company": {"$regex": "Blueberry", "$options": "i"}})
    docs = await cursor.to_list(length=10)
    for doc in docs:
        print(f"ID: {doc.get('id')} | Title: {doc.get('title')}")
        desc = doc.get("description", "")
        print("DESCRIPTION LINES:")
        for line in desc.split("\n")[:40]:
            print("  ", repr(line))
        print("="*60)

    # 2. Bosch Mobile & Hardware
    for jid in ["smartrecruiters_boschgroup_744000147203758", "smartrecruiters_boschgroup_744000147209508"]:
        doc = await coll.find_one({"id": jid})
        if doc:
            print(f"\nID: {doc.get('id')} | Title: {doc.get('title')}")
            desc = doc.get("description", "")
            print("DESCRIPTION LINES:")
            for line in desc.split("\n")[:30]:
                print("  ", repr(line))
            print("="*60)

    # 3. Check some Lever and Greenhouse jobs
    for src in ["lever", "greenhouse"]:
        doc = await coll.find_one({"source": src, "verification_status": "VERIFIED_ACTIVE"})
        if doc:
            print(f"\nID: {doc.get('id')} | Source: {src} | Title: {doc.get('title')}")
            desc = doc.get("description", "")
            print("DESCRIPTION LINES:")
            for line in desc.split("\n")[:30]:
                print("  ", repr(line))
            print("="*60)

    # 4. Check internship jobs
    doc = await coll.find_one({"job_type": "internship", "verification_status": "VERIFIED_ACTIVE"})
    if doc:
        print(f"\nINTERNSHIP: {doc.get('id')} | Title: {doc.get('title')}")
        desc = doc.get("description", "")
        print("DESCRIPTION LINES:")
        for line in desc.split("\n")[:30]:
            print("  ", repr(line))
        print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
