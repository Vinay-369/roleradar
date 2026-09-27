import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=5000)
    db = client["roleradar"]
    n = await db.jobs.count_documents({})
    print(f"Jobs in DB: {n}")
    client.close()

asyncio.run(main())
