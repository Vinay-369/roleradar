import asyncio
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "backend")

from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection
from app.modules.jobs.compensation_extractor import FALSE_POSITIVE_PATTERNS

ANY_MONEY_OR_COMP_REGEX = re.compile(
    r"(?:(?:₹|INR|Rs\.?|EUR|USD|\$)\s*[0-9][0-9,.]*|[0-9]+(?:\.[0-9]+)?\s*(?:lpa|lacs?|lakhs?|crores?|k|pm|per\s*month|per\s*annum))",
    re.I
)

async def print_all_14_fps():
    await connect_to_mongo()
    db = get_db()
    try:
        query = {
            "verification_status": "VERIFIED_ACTIVE",
            "country": "India",
            "source": {"$in": ["smartrecruiters", "lever", "greenhouse"]}
        }
        all_docs = await db.jobs.find(query).to_list(length=10000)
        found_fps = {}
        for doc in all_docs:
            desc = (doc.get("description") or "") + " " + (doc.get("raw_html") or "") + " " + (doc.get("jd_text") or "")
            for m in ANY_MONEY_OR_COMP_REGEX.finditer(desc):
                snippet = desc[max(0, m.start() - 160):min(len(desc), m.end() + 160)]
                for fp in FALSE_POSITIVE_PATTERNS:
                    if fp.search(snippet):
                        jid = doc["id"]
                        if jid not in found_fps:
                            found_fps[jid] = {
                                "id": jid,
                                "provider": doc["source"],
                                "company": doc["company"],
                                "title": doc["title"],
                                "matched": m.group(0),
                                "reason": fp.pattern,
                                "snippet": snippet.strip().replace("\n", " ")[:220]
                            }
                        break
        print(f"Total Unique FP Postings: {len(found_fps)}")
        for idx, (jid, item) in enumerate(found_fps.items(), 1):
            print(f"\n[{idx}] ID: {item['id']}")
            print(f"Provider: {item['provider']} | Company: {item['company']} | Title: {item['title']}")
            print(f"Token: {item['matched']}")
            print(f"Snippet: \"{item['snippet']}\"")
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(print_all_14_fps())
