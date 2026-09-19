import asyncio
import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
from app.db.mongo import connect_to_mongo, get_db

async def run():
    await connect_to_mongo()
    db = get_db()
    u = await db.users.find_one()
    if u:
        print(f"USER_ID={str(u['_id'])}")
    else:
        print("NO_USER")

if __name__ == "__main__":
    asyncio.run(run())
