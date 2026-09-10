import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def run_audit():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]

    # 1. Total jobs and status
    total = await db.jobs.count_documents({})
    active = await db.jobs.count_documents({"verification_status": "VERIFIED_ACTIVE"})
    print(f"Total jobs: {total}, Active: {active}")

    # 2. Check apply_url in active jobs
    with_apply = await db.jobs.count_documents({
        "verification_status": "VERIFIED_ACTIVE",
        "apply_url": {"$regex": r"^https?://"}
    })
    print(f"Active with http apply_url: {with_apply}")

    # 3. Check is_direct_apply
    direct_apply_count = await db.jobs.count_documents({
        "verification_status": "VERIFIED_ACTIVE",
        "is_direct_apply": True
    })
    print(f"Active with is_direct_apply True: {direct_apply_count}")

    # 4. Check active jobs where is_direct_apply is False or apply_url is missing
    cursor = db.jobs.find({
        "verification_status": "VERIFIED_ACTIVE",
        "$or": [
            {"apply_url": {"$not": {"$regex": r"^https?://"}}},
            {"is_direct_apply": False}
        ]
    })
    problematic = await cursor.to_list(length=50)
    print(f"Active with missing apply_url or is_direct_apply False: {len(problematic)}")
    for p in problematic[:10]:
        print(f"  [{p.get('source')}] {p.get('id')} - {p.get('company')} - {p.get('title')}")
        print(f"     apply_url: {p.get('apply_url')}")
        print(f"     is_direct_apply: {p.get('is_direct_apply')}, url_type: {p.get('url_type')}")

    # 5. Check the target Bosch mobile job: smartrecruiters_boschgroup_744000147203758
    print("\n--- TARGET BOSCH MOBILE JOB ---")
    bosch_mobile = await db.jobs.find_one({"id": "smartrecruiters_boschgroup_744000147203758"})
    if not bosch_mobile:
        # Check if ID exists with different prefix or in raw postings
        print("smartrecruiters_boschgroup_744000147203758 NOT found directly by id. Searching by partial id...")
        cand = await db.jobs.find_one({"id": {"$regex": "744000147203758"}})
        if cand:
            print("Found by regex:", cand.get("id"))
            bosch_mobile = cand
        else:
            print("Searching by title 'Senior Mobile APP'...")
            cand = await db.jobs.find_one({"title": {"$regex": "Senior Mobile APP", "$options": "i"}})
            if cand:
                print("Found by title:", cand.get("id"), cand.get("company"), cand.get("title"))
                bosch_mobile = cand

    if bosch_mobile:
        print("Bosch Mobile Document:")
        print("  id:", bosch_mobile.get("id"))
        print("  title:", bosch_mobile.get("title"))
        print("  company:", bosch_mobile.get("company"))
        print("  source:", bosch_mobile.get("source"))
        print("  apply_url:", bosch_mobile.get("apply_url"))
        print("  is_direct_apply:", bosch_mobile.get("is_direct_apply"))
        print("  verification_status:", bosch_mobile.get("verification_status"))
        print("  skills_required:", bosch_mobile.get("skills_required"))
        print("  skills_nice_to_have:", bosch_mobile.get("skills_nice_to_have"))
        print("  responsibilities count:", len(bosch_mobile.get("responsibilities", [])))
        print("  qualifications count:", len(bosch_mobile.get("qualifications", [])))
        print("  description length:", len(bosch_mobile.get("description", "")))
        print("  description preview (first 1000 chars):")
        print(bosch_mobile.get("description", "")[:1000])

if __name__ == "__main__":
    asyncio.run(run_audit())
