import asyncio
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection

async def check():
    await connect_to_mongo()
    db = get_db()
    try:
        total = await db.jobs.count_documents({})
        sal_disc = await db.jobs.count_documents({"salary_disclosed": True})
        sal_min = await db.jobs.count_documents({"salary_min": {"$ne": None}})
        stip_min = await db.jobs.count_documents({"stipend_min": {"$ne": None}})
        
        print(f"Total jobs in DB: {total}")
        print(f"Jobs with salary_disclosed == True: {sal_disc}")
        print(f"Jobs with salary_min != None: {sal_min}")
        print(f"Jobs with stipend_min != None: {stip_min}")
        
        if sal_min > 0:
            cursor = db.jobs.find({"salary_min": {"$ne": None}}).limit(5)
            async for j in cursor:
                print(f"  Sample: {j.get('id')} | {j.get('company')} | {j.get('salary_min')}–{j.get('salary_max')} {j.get('salary_currency')}")
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(check())
