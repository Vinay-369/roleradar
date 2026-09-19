import asyncio
import sys
sys.path.insert(0, "backend")

from motor.motor_asyncio import AsyncIOMotorClient

async def inspect_bosch_mobile():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]

    doc = await db.jobs.find_one({"id": "smartrecruiters_boschgroup_744000147203758"})
    if not doc:
        print("Not found!")
        return

    print("Location:", doc.get("location"))
    print("City:", doc.get("city"))
    print("Region:", doc.get("region"))
    print("Country:", doc.get("country"))
    print("Apply URL:", doc.get("apply_url"))
    print("is_direct_apply:", doc.get("is_direct_apply"))
    print("verification_status:", doc.get("verification_status"))
    print("Qualifications:", doc.get("qualifications"))
    print("Experience:", doc.get("experience_min"), "to", doc.get("experience_max"))
    print("Skills required:", doc.get("skills_required"))
    print("Skills nice to have:", doc.get("skills_nice_to_have"))

if __name__ == "__main__":
    asyncio.run(inspect_bosch_mobile())
