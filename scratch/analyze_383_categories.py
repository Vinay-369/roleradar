import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
sys.stdout.reconfigure(encoding="utf-8")
import json
from collections import Counter
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY

with open(r"c:\VINAY\roleradar\scratch\all_383_specialized_dump.json", encoding="utf-8") as f:
    items = json.load(f)

print(f"Loaded {len(items)} items")

# Let's inspect titles by company
by_comp = {}
for item in items:
    by_comp.setdefault(item["company"], []).append(item)

print("\n--- COMPANY BREAKDOWN ---")
for comp, c_items in sorted(by_comp.items(), key=lambda x: len(x[1]), reverse=True):
    print(f"\n{comp} ({len(c_items)} records):")
    for it in c_items[:10]:
        print(f"  - {it['title']}")
    if len(c_items) > 10:
        print(f"    ... and {len(c_items) - 10} more")
