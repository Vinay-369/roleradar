import asyncio
import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
from motor.motor_asyncio import AsyncIOMotorClient
from collections import Counter

async def check():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]
    coll = db["jobs"]
    
    all_docs = await coll.find({}).to_list(length=None)
    print(f"Total documents in db.jobs: {len(all_docs)}")

    india_docs = [d for d in all_docs if d.get("country") == "India"]
    print(f"\nTotal documents with country == 'India': {len(india_docs)}")
    print("  Sources:", Counter(d.get("source") for d in india_docs))
    print("  Verification Statuses:", Counter(d.get("verification_status") for d in india_docs))

    print("\nBreakdown by Source (country == 'India'):")
    for src in sorted(set(d.get("source", "unknown") for d in india_docs)):
        s_docs = [d for d in india_docs if d.get("source") == src]
        ver_counts = Counter(d.get("verification_status") for d in s_docs)
        print(f"  {src}: {len(s_docs)} total | {dict(ver_counts)}")

    # Let's inspect the 200 India docs that are NOT in the 588 VERIFIED_ACTIVE ATS
    non_verified_active = [d for d in india_docs if not (d.get("source") in ["smartrecruiters", "lever", "greenhouse"] and d.get("verification_status") == "VERIFIED_ACTIVE")]
    print(f"\nNon-ATS-Active India documents: {len(non_verified_active)}")
    print("  Sources:", Counter(d.get("source") for d in non_verified_active))
    print("  Verification statuses:", Counter(d.get("verification_status") for d in non_verified_active))

    # Check non-India documents
    non_india = [d for d in all_docs if d.get("country") != "India"]
    print(f"\nNon-India documents: {len(non_india)}")
    print("  Sources:", Counter(d.get("source") for d in non_india))
    print("  Top countries:", Counter(d.get("country") for d in non_india).most_common(10))

if __name__ == "__main__":
    asyncio.run(check())
