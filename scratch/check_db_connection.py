"""
Quick verification: Check if MongoDB is running and we can connect.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

async def check_connection():
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from app.core.config import get_settings
        from app.db.mongo import Collections

        settings = get_settings()
        print(f"Connecting to: {settings.MONGODB_URL}")

        client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
        db = client[settings.MONGODB_DB_NAME]

        # Try to count jobs
        count = await db[Collections.JOBS].count_documents({})
        print(f"✓ Successfully connected to MongoDB")
        print(f"✓ Found {count} jobs in database")

        await client.close()
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(check_connection())
    sys.exit(0 if success else 1)
