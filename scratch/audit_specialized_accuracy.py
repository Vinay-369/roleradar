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

# Get canonical role set from ROLE_TAXONOMY
canonical_roles_set = set(v.canonical_role for v in ROLE_TAXONOMY.values())
print(f"Total canonical roles in taxonomy: {len(canonical_roles_set)}")

# Collect unique live active Indian opportunities
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

print(f"Total Unique Live Active Indian Requisitions: {len(unique_india_active)}")

# Categorize documents
classified_in_db = []
specialized_in_db = []

for d in unique_india_active:
    crole = d.get("canonical_role")
    if crole and crole in canonical_roles_set and crole != "Specialized Requisition":
        classified_in_db.append(d)
    else:
        specialized_in_db.append(d)

print(f"\nAlready Classified into Canonical Roles in DB: {len(classified_in_db)}")
print(f"Specialized Requisitions in DB: {len(specialized_in_db)}")

# Now test what resolve_role(d.get("title")) produces for these specialized_in_db records!
can_resolve = []
cannot_resolve = []

for d in specialized_in_db:
    title = d.get("title") or ""
    prof, conf, reason = resolve_role(title)
    if prof and conf in ("HIGH", "MEDIUM"):
        can_resolve.append((d, prof, conf, reason))
    else:
        cannot_resolve.append((d, conf, reason))

print(f"\nOf the {len(specialized_in_db)} specialized records:")
print(f"  Directly resolvable by current resolve_role(title): {len(can_resolve)}")
print(f"  Not resolved by resolve_role(title): {len(cannot_resolve)}")

if can_resolve:
    print("\nSample records that CAN be resolved immediately from title:")
    resolved_roles_counter = Counter(prof.canonical_role for _, prof, _, _ in can_resolve)
    for r, count in resolved_roles_counter.most_common(20):
        print(f"    {r}: {count}")

print("\nExamining unresolved titles to see why taxonomy/parser didn't match:")
unresolved_titles = Counter(d.get("title") for d, _, _ in cannot_resolve)
for t, count in unresolved_titles.most_common(25):
    print(f"    [{count}x] {t}")
