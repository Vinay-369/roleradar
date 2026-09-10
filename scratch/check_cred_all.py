import asyncio
import sys
sys.path.insert(0, "backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text

async def check_all_5():
    client = AsyncIOMotorClient(get_settings().MONGO_URI)
    db = client[get_settings().MONGO_DB_NAME]
    cred_jobs = await db["jobs"].find({"company": {"$regex": "Cred", "$options": "i"}}).to_list(100)
    print(f"Total Cred jobs in DB: {len(cred_jobs)}")
    for j in cred_jobs:
        comp = extract_compensation_from_payload_and_text(j["description"], j.get("raw_payload"), False)
        print(f"ID: {j['id']} | Title: {j['title']}")
        print(f"  Stored in DB: salary_min={j.get('salary_min')}, salary_max={j.get('salary_max')}")
        print(f"  Extractor:    salary_min={comp.salary_min}, salary_max={comp.salary_max}, disclosed={comp.salary_disclosed}")

if __name__ == "__main__":
    asyncio.run(check_all_5())
