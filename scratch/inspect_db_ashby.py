import sys
sys.path.insert(0, 'backend')
from app.core.database import get_database

db = get_database()
ashby_jobs = list(db.opportunities.find({"source": "ashby"}))
print(f"Total Ashby jobs in DB: {len(ashby_jobs)}")

india_jobs = [j for j in ashby_jobs if j.get("is_india_opportunity")]
print(f"Total Ashby India jobs in DB: {len(india_jobs)}")

by_company = {}
for j in india_jobs:
    comp = j.get("company", "Unknown")
    by_company.setdefault(comp, []).append(j)

for comp, jobs in by_company.items():
    print(f"\n--- {comp} ({len(jobs)} jobs) ---")
    for j in jobs:
        print(f"  Title: {j.get('title')}")
        print(f"  Location: {j.get('location')}")
        print(f"  Canonical Role: {j.get('canonical_role')}")
        print(f"  Confidence: {j.get('mapping_confidence')}")
        print(f"  Apply URL: {j.get('application_url')}")
