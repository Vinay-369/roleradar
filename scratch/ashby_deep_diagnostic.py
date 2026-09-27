"""
Phase 13C: Deep diagnostic of Ashby unclassified roles and location integrity.
"""
import asyncio
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import sys

sys.path.insert(0, r"c:\VINAY\roleradar\backend")

from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongo import Collections
from app.modules.learning.role_taxonomy import resolve_role

NON_INDIA_SIGNALS = {
    "united kingdom", "uk", "london", "manchester", "germany", "berlin",
    "singapore", "san francisco", "united states", "usa", "new york",
    "california", "austin", "seattle", "boston", "toronto", "canada",
    "australia", "sydney", "amsterdam", "paris", "france",
}

async def main():
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=10000)
    db = client["roleradar"]
    coll = db[Collections.JOBS]

    # Fetch all India Active Ashby jobs
    cursor = coll.find({
        "source": "ashby",
        "verification_status": "VERIFIED_ACTIVE",
        "is_india_opportunity": True
    })
    docs = await cursor.to_list(length=2000)
    print(f"Total India Active Ashby: {len(docs)}\n")

    # --- 1. Unclassified role titles ---
    print("=" * 65)
    print("UNCLASSIFIED ROLES (no canonical match HIGH/MEDIUM)")
    print("=" * 65)
    unclassified = []
    classified = []
    for doc in docs:
        title = doc.get("title", "")
        prof, conf, _ = resolve_role(title)
        c_role = prof.canonical_role if prof else None
        if not prof or conf not in ("HIGH", "MEDIUM"):
            unclassified.append({
                "title": title,
                "canonical": c_role,
                "conf": conf,
                "location": doc.get("location", ""),
                "board": doc.get("board_slug", doc.get("board", "")),
                "url": doc.get("apply_url", ""),
            })
        else:
            classified.append({
                "title": title,
                "canonical": c_role,
                "conf": conf,
            })

    print(f"\nUnclassified count: {len(unclassified)}")
    for u in sorted(unclassified, key=lambda x: x["title"]):
        conf_str = u["conf"] or "NONE"
        role_str = u["canonical"] or "-"
        print(f"  [{conf_str:6}] [{u['board']:12}] {u['title']:<50} -> {role_str}")

    print(f"\nClassified count: {len(classified)}")
    for c in sorted(classified, key=lambda x: x["title"]):
        print(f"  [{c['conf']:6}] {c['title']:<50} -> {c['canonical']}")

    # --- 2. Location integrity check ---
    print("\n" + "=" * 65)
    print("LOCATION INTEGRITY — Non-India locations flagged is_india=True")
    print("=" * 65)
    suspicious = []
    for doc in docs:
        loc = (doc.get("location") or "").lower().strip()
        if any(sig in loc for sig in NON_INDIA_SIGNALS):
            suspicious.append({
                "title": doc.get("title", ""),
                "location": doc.get("location", ""),
                "board": doc.get("board_slug", doc.get("board", "")),
                "job_type": doc.get("job_type", ""),
                "departments": doc.get("departments", []),
                "url": doc.get("apply_url", ""),
            })

    if suspicious:
        print(f"\n⚠ {len(suspicious)} jobs have non-India locations but is_india_opportunity=True:")
        for s in suspicious:
            print(f"  [{s['board']:12}] {s['title']:<45} | {s['location']}")
    else:
        print("\n✓ No location integrity issues found.")

    # --- 3. Unique unclassified title tokens for taxonomy analysis ---
    print("\n" + "=" * 65)
    print("UNIQUE UNCLASSIFIED TITLE WORDS (for taxonomy gap analysis)")
    print("=" * 65)
    from collections import Counter
    import re
    token_counter = Counter()
    STOPWORDS = {"and", "or", "of", "the", "a", "an", "in", "for", "to", "at",
                 "senior", "junior", "lead", "staff", "principal", "mid", "entry"}
    for u in unclassified:
        tokens = re.findall(r"[a-z]+", u["title"].lower())
        for t in tokens:
            if t not in STOPWORDS and len(t) > 2:
                token_counter[t] += 1
    print("\nTop tokens in unclassified titles:")
    for token, cnt in token_counter.most_common(30):
        print(f"  {token:<25}: {cnt}")

    client.close()

asyncio.run(main())
