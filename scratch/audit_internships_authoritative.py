import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from pymongo import MongoClient
from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location
from app.modules.jobs.deduplication import compute_dedup_key
from collections import Counter

client = MongoClient("127.0.0.1:27017")
db = client["roleradar"]
coll = db["jobs"]

seen_keys = set()
unique_india_active = []
for d in coll.find({"source": {"$in": ["smartrecruiters", "lever", "greenhouse"]}, "verification_status": "VERIFIED_ACTIVE"}):
    country = (d.get("country") or "").strip()
    loc = (d.get("location") or "").strip()
    if country.lower() in ["india", "in"] or is_india_opportunity(loc) or extract_country_from_location(loc) == "India":
        k = compute_dedup_key(d.get("company", ""), d.get("title", ""), d.get("location", ""), d.get("job_type", "full_time"), d.get("is_remote", False))
        if k not in seen_keys:
            seen_keys.add(k)
            unique_india_active.append(d)

internships = [d for d in unique_india_active if d.get("job_type") == "internship"]
print(f"Total Authoritative Internships in India: {len(internships)}")

for i in internships:
    desc_len = len(d.get("description") or d.get("jd_text") or "")
    print(f"  [{i.get('company')}] '{i.get('title')}' -> canonical_role: '{i.get('canonical_role')}' | type: {i.get('job_type')} | apply_url: {i.get('apply_url')[:45]}...")

counts = Counter(i.get("canonical_role") for i in internships)
print("\nInternship Role Coverage Breakdown:")
for r, c in counts.most_common():
    print(f"  {r}: {c}")
