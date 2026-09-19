import asyncio
import sys
sys.path.insert(0, "backend")
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.completeness import evaluate_opportunity_completeness

async def check():
    client = AsyncIOMotorClient(get_settings().MONGO_URI)
    db = client[get_settings().MONGO_DB_NAME]
    doc = await db[Collections.JOBS].find_one({"completeness_status": "INSUFFICIENT"})
    if doc:
        print("ID:", doc.get("id"))
        print("Title:", doc.get("title"))
        print("Company:", doc.get("company"))
        print("Description length:", len(doc.get("description", "")))
        print("Description preview:", doc.get("description", "")[:200])
        res = evaluate_opportunity_completeness(doc)
        print("Missing required:", res.missing_required_information)
        print("Quality:", res.recommendation_quality)
        print("Source completeness:", res.source_completeness)

if __name__ == "__main__":
    asyncio.run(check())
