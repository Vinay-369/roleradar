import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_db():
    from app.db.mongo import Collections
    from app.core.config import get_settings
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    
    resume = await db[Collections.RESUMES].find_one({"is_active": True})
    if resume:
        parsed = resume.get("parsed")
        print("Type of parsed:", type(parsed))
        if isinstance(parsed, str):
            print("Parsed is a string:", parsed[:100])
        else:
            print("Parsed is a dict, keys:", parsed.keys() if parsed else "None")
    else:
        print("No active resume found")

if __name__ == "__main__":
    asyncio.run(check_db())
