import json
import re
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.modules.learning.role_taxonomy import resolve_role, ROLE_TAXONOMY

with open("scratch/all_383_specialized_dump.json", "r", encoding="utf-8") as f:
    records = json.load(f)

remapped = []
preserved = []

for r in records:
    title = r["title"]
    profile, conf, key = resolve_role(title)
    if profile:
        remapped.append({
            "id": r["id"],
            "title": title,
            "company": r["company"],
            "new_role": profile.canonical_role,
            "domain": profile.domain,
        })
    else:
        preserved.append({
            "id": r["id"],
            "title": title,
            "company": r["company"],
        })

print(f"Total 383 records audited:")
print(f"  Remapped with evidence: {len(remapped)}")
print(f"  Preserved as Specialized: {len(preserved)}")
print("\nBreakdown of Remapped Roles:")
counts = {}
for item in remapped:
    counts[item["new_role"]] = counts.get(item["new_role"], 0) + 1

for role, cnt in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"  {role}: {cnt}")

print("\nDetail of remapped records:")
for item in remapped:
    print(f"  [{item['company']}] '{item['title']}' -> {item['new_role']} ({item['domain']})")
