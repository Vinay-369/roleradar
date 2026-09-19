import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
import pymongo
from collections import Counter
from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location
from app.modules.jobs.deduplication import compute_dedup_key

client = pymongo.MongoClient("127.0.0.1:27017")
db = client["roleradar"]
coll = db["jobs"]

all_docs = list(coll.find({}))
print(f"Total documents in database: {len(all_docs)}")

# Source breakdown
sources = Counter(d.get("source") for d in all_docs)
print("Sources in DB:", dict(sources))

# Check Direct ATS active
direct_ats = [d for d in all_docs if d.get("source") in ["smartrecruiters", "lever", "greenhouse"]]
print(f"Total Direct ATS: {len(direct_ats)}")

# Split by active and India
active_direct_ats = [d for d in direct_ats if d.get("verification_status") == "VERIFIED_ACTIVE"]
print(f"Total VERIFIED_ACTIVE Direct ATS: {len(active_direct_ats)}")

india_active = []
for d in active_direct_ats:
    country = (d.get("country") or "").strip()
    loc = (d.get("location") or "").strip()
    if country.lower() in ["india", "in"] or is_india_opportunity(loc) or extract_country_from_location(loc) == "India":
        india_active.append(d)

print(f"Total Live Active Indian Requisitions: {len(india_active)}")
print("Provider breakdown for Live Active Indian:", dict(Counter(d["source"] for d in india_active)))

# Check deduplication on india_active
seen_keys = set()
unique_india_active = []
duplicates = []
for d in india_active:
    k = compute_dedup_key(d.get("company", ""), d.get("title", ""), d.get("location", ""), d.get("job_type", "full_time"), d.get("is_remote", False))
    if k in seen_keys:
        duplicates.append(d)
    else:
        seen_keys.add(k)
        unique_india_active.append(d)

print(f"Duplicates within Live Active Indian: {len(duplicates)}")
for dup in duplicates:
    print(f"  Duplicate ID: {dup.get('id')} | Company: {dup.get('company')} | Title: {dup.get('title')} | Source: {dup.get('source')}")

print(f"Unique Live Active Indian: {len(unique_india_active)}")
print("Provider breakdown for Unique Live Active Indian:", dict(Counter(d["source"] for d in unique_india_active)))

# Now check the 588 vs 587 question:
# Look at len(india_active) = 588 vs unique_india_active = 587!
# One Greenhouse InMobi job was duplicate:
# Let's also check if there's any job with description < 50 characters or invalid apply URL
stub_jobs = [d for d in unique_india_active if len((d.get("description") or d.get("jd_text") or "").strip()) < 50]
print(f"Jobs with description < 50 chars: {len(stub_jobs)}")
for s in stub_jobs:
    print(f"  Stub ID: {s.get('id')} | Company: {s.get('company')} | Title: {s.get('title')} | Desc len: {len((s.get('description') or s.get('jd_text') or '').strip())}")

# Check Greenhouse Apply URLs
gh_india = [d for d in unique_india_active if d.get("source") == "greenhouse"]
print(f"\nGreenhouse unique active India count: {len(gh_india)}")
gh_apply_types = Counter(d.get("apply_url_type") for d in gh_india)
print("Greenhouse apply_url_type distribution:", dict(gh_apply_types))
gh_is_direct = Counter(d.get("is_direct_apply") for d in gh_india)
print("Greenhouse is_direct_apply distribution:", dict(gh_is_direct))
gh_urls = [d.get("apply_url") for d in gh_india]
valid_urls = [u for u in gh_urls if u and ("http://" in u or "https://" in u)]
print(f"Greenhouse valid HTTP apply URLs: {len(valid_urls)} / {len(gh_india)}")
direct_domains = [u for u in gh_urls if u and ("greenhouse.io" in u or "boards.greenhouse.io" in u)]
print(f"Greenhouse domain URLs: {len(direct_domains)} / {len(gh_india)}")
non_gh_domains = [u for u in gh_urls if u and ("greenhouse.io" not in u and "boards.greenhouse.io" not in u)]
print(f"Greenhouse non-greenhouse domain URLs: {len(non_gh_domains)}")
for u in non_gh_domains[:5]:
    print("  Sample non-greenhouse URL:", u)
