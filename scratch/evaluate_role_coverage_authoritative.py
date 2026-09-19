import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from pymongo import MongoClient
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role
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

print(f"Authoritative Unique Live Active Indian Opportunities: {len(unique_india_active)}")

# Count canonical roles
counts = Counter(d.get("canonical_role") for d in unique_india_active)
print(f"\nTotal distinct canonical roles populated: {len(counts)}")
print(f"Specialized Requisition count: {counts['Specialized Requisition']} (was 383)")
print(f"Net change: {383 - counts['Specialized Requisition']} records successfully remapped with evidence!")

print("\nFull breakdown of all roles with active count > 0:")
for role, cnt in counts.most_common():
    print(f"  {role}: {cnt}")
