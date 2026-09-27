"""
Phase 13C: Inspect the raw stored data for the 8 suspicious India-flagged jobs
with non-India primary locations.
"""
import asyncio
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, r"c:\VINAY\roleradar\backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongo import Collections

SUSPECT_TITLES = {
    "Revenue Compensation Lead",
    "Revenue Strategy & Operations - APAC",
    "Dubbing Specialist (Freelance)",
    "APAC Communications",
    "Audiobook Specialists (Freelance)",
    "Systems Architect",
    "Translator/Linguist (Freelance)",
    "Transcription / Subtitling Specialist (Freelance)",
}

NON_INDIA_LOC = {"united states", "singapore", "united kingdom", "germany", "san francisco"}

async def main():
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=10000)
    db = client["roleradar"]
    coll = db[Collections.JOBS]

    cursor = coll.find({
        "source": "ashby",
        "verification_status": "VERIFIED_ACTIVE",
        "is_india_opportunity": True
    })
    docs = await cursor.to_list(length=2000)

    print(f"Checking {len(docs)} India Active Ashby jobs for suspicious location/flag combo\n")
    print("=" * 80)
    for doc in docs:
        title = doc.get("title", "")
        loc = (doc.get("location") or "").strip()
        if any(sig in loc.lower() for sig in NON_INDIA_LOC):
            print(f"TITLE   : {title}")
            print(f"LOCATION: {loc}")
            print(f"COUNTRY : {doc.get('country', 'N/A')}")
            print(f"IS_INDIA: {doc.get('is_india_opportunity')}")
            print(f"IS_REMOTE: {doc.get('is_remote', 'N/A')}")
            print(f"WORKPLACE: {doc.get('workplace_type', 'N/A')}")
            print(f"JOB_TYPE: {doc.get('job_type', 'N/A')}")
            print(f"URL     : {doc.get('apply_url', 'N/A')[:80]}")
            # Show all location-related raw fields
            raw_location = doc.get("raw_location", doc.get("location_raw", "N/A"))
            print(f"SEC_LOCS: {doc.get('secondary_locations', 'N/A')}")
            print(f"BOARD   : {doc.get('board', doc.get('board_slug', 'N/A'))}")
            print("-" * 80)

    client.close()

asyncio.run(main())
