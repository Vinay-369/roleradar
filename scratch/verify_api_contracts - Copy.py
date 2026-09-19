import asyncio
import json
import sys
sys.path.insert(0, ".")

from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient
from app.main import app
from app.core.config import get_settings

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]
    jobs_coll = db["jobs"]
    users_coll = db["users"]

    # Grab a real or mock user to authenticate / mock auth
    test_user = await users_coll.find_one({})
    if not test_user:
        print("No user in DB")
        return

    settings = get_settings()
    from app.db.mongo import connect_to_mongo
    await connect_to_mongo()
    from app.core.security import create_access_token
    token = create_access_token(subject=str(test_user["_id"]), settings=settings)
    headers = {"Authorization": f"Bearer {token}"}

    sample_ids = [
        "smartrecruiters_boschgroup_744000147203758",  # Bosch Mobile
        "smartrecruiters_boschgroup_744000147209508",  # Bosch Hardware
        "smartrecruiters_blueberrylabsprivatelimited_101534578", # Blueberry Labs
        "lever_paytm_00099566-d2c0-4071-a9c0-8c09bfb5f9f3", # Lever
        "gh_groww_4588364101", # Greenhouse
    ]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for jid in sample_ids:
            doc = await jobs_coll.find_one({"id": jid})
            if not doc:
                print(f"ERROR: {jid} not in DB")
                continue

            resp = await ac.get(f"/api/jobs/{jid}", headers=headers)
            if resp.status_code != 200:
                print(f"ERROR: GET /api/jobs/{jid} returned {resp.status_code}")
                continue

            api_data = resp.json()

            mongo_apply = doc.get("apply_url")
            api_apply = api_data.get("apply_url")
            mongo_direct = doc.get("is_direct_apply")
            api_direct = api_data.get("is_direct_apply")
            mongo_status = doc.get("verification_status")
            api_status = api_data.get("verification_status")

            match_apply = (mongo_apply == api_apply)
            match_direct = (mongo_direct == api_direct)
            match_status = (mongo_status == api_status)

            print(f"\n--- Opportunity: {jid} ---")
            print(f"Title: {api_data.get('title')}")
            print(f"apply_url match: {match_apply} (Mongo='{mongo_apply}' == API='{api_apply}')")
            print(f"is_direct_apply match: {match_direct} (Mongo={mongo_direct} == API={api_direct})")
            print(f"verification_status match: {match_status} (Mongo='{mongo_status}' == API='{api_status}')")

if __name__ == "__main__":
    asyncio.run(main())
