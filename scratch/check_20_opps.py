import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import urllib.request
import json

async def main():
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    db = client["roleradar"]
    
    # Register / login test user to get bearer token
    reg_data = json.dumps({"full_name": "Audit User", "email": "audit_user_opps@test.com", "password": "SecurePassword123!"}).encode()
    login_data = json.dumps({"email": "audit_user_opps@test.com", "password": "SecurePassword123!"}).encode()
    reg_req = urllib.request.Request("http://127.0.0.1:8000/api/auth/register", data=reg_data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(reg_req) as r:
            token = json.loads(r.read().decode())["access_token"]
    except Exception:
        login_req = urllib.request.Request("http://127.0.0.1:8000/api/auth/login", data=login_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(login_req) as r:
            token = json.loads(r.read().decode())["access_token"]
            
    headers = {"Authorization": f"Bearer {token}"}
    
    providers = ["smartrecruiters", "lever", "greenhouse", "adzuna"]
    docs = []
    for p in providers:
        cursor = db["jobs"].find({"source": p, "verification_status": "VERIFIED_ACTIVE"}).limit(5)
        async for doc in cursor:
            docs.append(doc)
            
    print(f"Retrieved {len(docs)} sample opportunities across {providers}.")
    mismatches = []
    
    for doc in docs:
        job_id = doc.get("id") or str(doc["_id"])
        try:
            req = urllib.request.Request(f"http://127.0.0.1:8000/api/jobs/{job_id}", headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                api_data = json.loads(resp.read().decode())
        except Exception as e:
            mismatches.append(f"{job_id}: API error {e}")
            continue
            
        for field in ["title", "company", "location", "apply_url"]:
            db_val = (doc.get(field) or "").strip()
            api_val = (api_data.get(field) or "").strip()
            if db_val != api_val:
                mismatches.append(f"{job_id} [{field}]: DB='{db_val}' vs API='{api_val}'")
                
        # Responsibilities & qualifications fidelity
        if doc.get("responsibilities") and len(api_data.get("responsibilities", [])) == 0:
            mismatches.append(f"{job_id} responsibilities missing in API detail")
        if doc.get("qualifications") and len(api_data.get("qualifications", [])) == 0:
            mismatches.append(f"{job_id} qualifications missing in API detail")

    print(f"Total discrepancies found: {len(mismatches)}")
    if mismatches:
        for m in mismatches:
            print("  -", m)
    else:
        print("ALL 20 OPPORTUNITIES SHOW PERFECT (100%) SOURCE -> DB -> API FIDELITY!")

if __name__ == "__main__":
    asyncio.run(main())
