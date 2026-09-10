import asyncio
import sys
sys.path.insert(0, "backend")

import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.mongo import Collections

async def test_live_api():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Find a test user or create token
    user = await db[Collections.USERS].find_one({})
    if not user:
        print("No user found in DB")
        return

    token = create_access_token(str(user["_id"]), settings)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30.0) as http_client:
        # 1. Jobs search
        res = await http_client.get("/api/jobs?region=india&limit=5", headers=headers)
        print("Jobs Search Status:", res.status_code)
        jobs = res.json()
        print("Jobs Count:", len(jobs))
        for j in jobs[:2]:
            print("Job:", j["title"], "| Company:", j["company"], "| Completeness:", j.get("completeness_status"), "| Direct:", j.get("is_direct_apply"))

        # 2. Internships search
        res_intern = await http_client.get("/api/jobs?region=india&opportunity_type=INTERNSHIP&limit=5", headers=headers)
        print("\nInternships Search Status:", res_intern.status_code)
        interns = res_intern.json()
        print("Internships Count:", len(interns))
        for i in interns[:2]:
            print("Internship:", i["title"], "| Company:", i["company"], "| Completeness:", i.get("completeness_status"), "| Type:", i.get("opportunity_type"))

        # 3. Single Job Detail
        if jobs:
            first_id = jobs[0]["id"]
            res_detail = await http_client.get(f"/api/jobs/{first_id}", headers=headers)
            print("\nJob Detail Status:", res_detail.status_code)
            detail = res_detail.json()
            print("Detail Title:", detail.get("title"))
            print("Detail Completeness:", detail.get("completeness_status"))
            print("Employer Skills:", detail.get("skills_required")[:5] if detail.get("skills_required") else "None disclosed")
            print("Qualifications:", detail.get("qualifications")[:3] if detail.get("qualifications") else "None disclosed")
            print("Responsibilities:", detail.get("responsibilities")[:3] if detail.get("responsibilities") else "None disclosed")
            print("Direct Apply URL:", detail.get("apply_url"))

        # 4. Search for Blueberry Labs Full Stack Developer (verifying experience and skills)
        res_bb = await http_client.get("/api/jobs?search=Full+Stack&region=india", headers=headers)
        bb_jobs = res_bb.json()
        bb_full_stack = [j for j in bb_jobs if "Blueberry" in j.get("company", "")]
        if bb_full_stack:
            bb_id = bb_full_stack[0]["id"]
            res_bb_detail = await http_client.get(f"/api/jobs/{bb_id}", headers=headers)
            bb_detail = res_bb_detail.json()
            print("\nBlueberry Detail Title:", bb_detail.get("title"))
            print("Blueberry Completeness:", bb_detail.get("completeness_status"))
            print("Blueberry Experience:", bb_detail.get("experience_min"), "to", bb_detail.get("experience_max"), "years")
            print("Blueberry Skills:", bb_detail.get("skills_required"))
            print("Blueberry Qualifications:", bb_detail.get("qualifications"))
            print("Blueberry Apply URL:", bb_detail.get("apply_url"))

if __name__ == "__main__":
    asyncio.run(test_live_api())
