import asyncio
import sys
sys.path.insert(0, "backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text

async def inspect():
    client = AsyncIOMotorClient(get_settings().MONGO_URI)
    db = client[get_settings().MONGO_DB_NAME]
    doc = await db["jobs"].find_one({"id": "lever_cred_fa6c100a-0fe0-4892-a8a3-8d2169d5005e"})
    print("Title:", doc["title"])
    desc = doc["description"]
    print("Description around rupee symbol:")
    idx = desc.find("\u20b9")
    if idx != -1:
        print(desc[max(0, idx - 100):min(len(desc), idx + 100)].encode("ascii", "replace").decode())
    else:
        print("Rupee symbol not found by literal search")

    comp = extract_compensation_from_payload_and_text(doc["description"], doc.get("raw_payload"), False)
    print("\nExtractor result:")
    print("salary_min:", comp.salary_min)
    print("salary_max:", comp.salary_max)
    print("salary_disclosed:", comp.salary_disclosed)
    print("compensation_type:", comp.compensation_type)
    print("compensation_text:", comp.compensation_text)

if __name__ == "__main__":
    asyncio.run(inspect())
