import asyncio
import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
from motor.motor_asyncio import AsyncIOMotorClient

async def check_comp():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]

    # Sanitize stale salary_disclosed flags where compensation_type is UNDISCLOSED and no numeric salary
    res = await db.jobs.update_many(
        {
            "compensation_type": "UNDISCLOSED",
            "salary_min": None,
            "salary_max": None,
            "salary_disclosed": True
        },
        {"$set": {"salary_disclosed": False}}
    )
    print(f"Sanitized {res.modified_count} stale salary_disclosed flags to False.")

    primary = await db.jobs.find({
        "country": "India",
        "verification_status": "VERIFIED_ACTIVE",
        "completeness_status": "VERIFIED_COMPLETE"
    }).to_list(length=None)
    
    numeric_sal = [j for j in primary if j.get("salary_min") is not None or j.get("salary_max") is not None]
    numeric_stipend = [j for j in primary if j.get("stipend_min") is not None or j.get("stipend_max") is not None or j.get("stipend") is not None]
    disclosed_flag = [j for j in primary if j.get("salary_disclosed")]
    comp_types = {}
    for j in primary:
        ct = j.get("compensation_type", "UNDISCLOSED")
        comp_types[ct] = comp_types.get(ct, 0) + 1
        
    print(f"Total Primary Recommendations: {len(primary)}")
    print(f"Numeric Salary Count: {len(numeric_sal)}")
    print(f"Numeric Stipend Count: {len(numeric_stipend)}")
    print(f"Disclosed Flag Count: {len(disclosed_flag)}")
    print(f"Compensation Types Breakdown: {comp_types}")
    print(f"  Qualitative (e.g. competitive/market standard text): {comp_types.get('QUALITATIVE', 0)}")
    print(f"  Undisclosed: {comp_types.get('UNDISCLOSED', 0)}")

if __name__ == "__main__":
    asyncio.run(check_comp())
