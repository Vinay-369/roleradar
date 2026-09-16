import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def audit():
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    db = client["roleradar"]
    
    docs = await db["jobs"].find({"country": "India"}).to_list(10000)
    print(f"Total Indian opportunities checked: {len(docs)}")
    
    # Deduplication test: Check for duplicates by (company, title, location)
    seen = {}
    dupes = []
    for d in docs:
        key = (
            (d.get("company") or "").lower().strip(),
            (d.get("title") or "").lower().strip(),
            (d.get("location") or "").lower().strip()
        )
        if key in seen:
            dupes.append((d, seen[key]))
        else:
            seen[key] = d
            
    print(f"Duplicate count by (company, title, location): {len(dupes)}")
    
    # Freshness check: Check posted_at or created_at
    has_date = sum(1 for d in docs if d.get("created_at") or d.get("posted_at") or d.get("released_date"))
    print(f"Opportunities with verified timestamp: {has_date} ({round(has_date/len(docs)*100, 1)}%)")
    
    # Apply link integrity
    valid_apply = sum(1 for d in docs if (d.get("apply_url") or "").startswith(("http://", "https://")))
    print(f"Valid Apply URLs: {valid_apply} ({round(valid_apply/len(docs)*100, 1)}%)")

if __name__ == "__main__":
    asyncio.run(audit())
