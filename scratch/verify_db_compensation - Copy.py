import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "backend")

from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection
from collections import Counter

async def main():
    await connect_to_mongo()
    db = get_db()
    try:
        query = {
            "verification_status": "VERIFIED_ACTIVE",
            "country": "India",
            "source": {"$in": ["smartrecruiters", "lever", "greenhouse"]}
        }
        cursor = db.jobs.find(query)
        type_counter = Counter()
        text_counter = Counter()
        prov_counter = Counter()

        async for job in cursor:
            c_type = job.get("compensation_type")
            c_text = job.get("compensation_text")
            prov = job.get("source")
            type_counter[c_type] += 1
            if c_text:
                text_counter[c_text] += 1
                prov_counter[prov] += 1

        print("Compensation Types across all 587 live Indian opportunities:")
        for t, cnt in type_counter.items():
            print(f"  {t}: {cnt} ({cnt/587*100:.2f}%)")

        print("\nCompensation Texts Disclosed:")
        for txt, cnt in text_counter.items():
            print(f"  '{txt}': {cnt}")

        print("\nDisclosures by Provider:")
        for p, cnt in prov_counter.items():
            print(f"  {p}: {cnt}")

    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
