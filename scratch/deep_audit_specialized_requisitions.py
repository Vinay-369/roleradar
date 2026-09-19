import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
import pymongo
from collections import Counter
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role
from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location
from app.modules.jobs.deduplication import compute_dedup_key

client = pymongo.MongoClient("127.0.0.1:27017")
db = client["roleradar"]
coll = db["jobs"]

# Get unique live active Indian opportunities
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

print(f"Total unique live active Indian: {len(unique_india_active)}")

# Identify all records currently classified as "Specialized Requisition"
# Note: check both d.get("canonical_role") and what resolve_role(d.get("title")) produces
specialized_records = []
for d in unique_india_active:
    crole = d.get("canonical_role")
    if not crole or crole == "Specialized Requisition" or crole == d.get("title"):
        specialized_records.append(d)

print(f"Total Specialized Requisition records: {len(specialized_records)}")

# Let's inspect the titles and companies of these specialized records
title_counts = Counter(d.get("title") for d in specialized_records)
print(f"\nDistinct titles in Specialized Requisitions: {len(title_counts)}")
print("Top 30 titles in Specialized Requisitions:")
for t, c in title_counts.most_common(30):
    print(f"  [{c}x] {t}")

# Company breakdown for specialized
comp_counts = Counter(d.get("company") for d in specialized_records)
print("\nTop 15 companies in Specialized Requisitions:")
for comp, c in comp_counts.most_common(15):
    print(f"  [{c}x] {comp}")
