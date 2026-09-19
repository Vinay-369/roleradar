import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import json
from app.modules.learning.role_taxonomy import resolve_role

with open("scratch/all_383_specialized_dump.json", "r", encoding="utf-8") as f:
    orig_383 = json.load(f)

orig_383_ids = {r["id"] for r in orig_383}

from pymongo import MongoClient
client = MongoClient("127.0.0.1:27017")
db = client["roleradar"]
coll = db["jobs"]

all_sr = list(coll.find({"canonical_role": "Specialized Requisition", "country": "India", "verification_status": "VERIFIED_ACTIVE"}))

print(f"Total current SR in DB: {len(all_sr)}")
new_sr_not_in_orig = [d for d in all_sr if d.get("id") not in orig_383_ids]
print(f"SR docs that were NOT in original 383: {len(new_sr_not_in_orig)}")
for d in new_sr_not_in_orig:
    print(f"  [{d.get('company')}] '{d.get('title')}'")
