import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
import pymongo
from app.modules.learning.role_taxonomy import resolve_role

client = pymongo.MongoClient("127.0.0.1:27017")
db = client["roleradar"]
coll = db["jobs"]

# Find records with title "Project Manager" or "Graphic Designer"
for t in ["Project Manager", "Graphic Designer"]:
    docs = list(coll.find({"title": t, "verification_status": "VERIFIED_ACTIVE"}))
    print(f"\nTitle '{t}' found: {len(docs)}")
    for d in docs:
        prof, conf, reason = resolve_role(t)
        print(f"  ID: {d.get('id')} | Company: {d.get('company')} | canonical_role in doc: '{d.get('canonical_role')}' | resolve_role returns: {prof.canonical_role if prof else None} ({conf}, {reason})")
