import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
sys.stdout.reconfigure(encoding="utf-8")
import pymongo
import json
import re
from collections import Counter
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role, _normalize_role_input
from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location
from app.modules.jobs.deduplication import compute_dedup_key

client = pymongo.MongoClient("127.0.0.1:27017")
db = client["roleradar"]
coll = db["jobs"]

canonical_roles_set = set(v.canonical_role for v in ROLE_TAXONOMY.values())

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

specialized_records = [d for d in unique_india_active if not d.get("canonical_role") or d.get("canonical_role") not in canonical_roles_set or d.get("canonical_role") == "Specialized Requisition"]

print(f"Total specialized records to audit: {len(specialized_records)}")

# Let's inspect all 383 titles and companies and dump them to a JSON file for deep inspection
audit_items = []
for idx, d in enumerate(specialized_records):
    t = d.get("title") or ""
    c = d.get("company") or ""
    desc = d.get("description") or d.get("jd_text") or ""
    skills = d.get("skills_required") or []
    
    # Check what resolve_role says on title
    prof, conf, reason = resolve_role(t)
    
    # Also clean title (e.g. replace mojibake  with -)
    clean_t = t.replace("", "-").replace("–", "-").replace("—", "-")
    prof_clean, conf_clean, reason_clean = resolve_role(clean_t)

    audit_items.append({
        "id": d.get("id"),
        "title": t,
        "clean_title": clean_t,
        "company": c,
        "opportunity_type": d.get("opportunity_type"),
        "location": d.get("location"),
        "desc_snippet": desc[:200].replace("\n", " ").strip(),
        "skills": skills[:5],
        "current_resolve": prof.canonical_role if prof else None,
        "current_conf": conf,
        "current_reason": reason,
        "clean_resolve": prof_clean.canonical_role if prof_clean else None,
        "clean_conf": conf_clean,
        "clean_reason": reason_clean
    })

with open(r"c:\VINAY\roleradar\scratch\all_383_specialized_dump.json", "w", encoding="utf-8") as f:
    json.dump(audit_items, f, indent=2)

print("Saved all 383 records to scratch/all_383_specialized_dump.json")

# Let's check how many clean_title resolved
clean_resolves = [item for item in audit_items if item["clean_resolve"]]
print(f"Simply cleaning hyphens/mojibake resolves: {len(clean_resolves)} records")
for cr in clean_resolves:
    print(f"  '{cr['title']}' -> {cr['clean_resolve']} ({cr['clean_conf']}, {cr['clean_reason']})")
