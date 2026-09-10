import json

with open("scratch/phase17_correction_report_authoritative.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Let's read evaluated_docs from scratch/generate_authoritative_correction_report.py
# Or compute directly
from pymongo import MongoClient
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location
from app.modules.jobs.deduplication import compute_dedup_key
from app.modules.jobs.completeness import evaluate_opportunity_completeness

client = MongoClient("127.0.0.1:27017")
coll = client["roleradar"]["jobs"]

seen = set()
unique_docs = []
for d in coll.find({"verification_status": "VERIFIED_ACTIVE"}):
    country = (d.get("country") or "").strip()
    loc = (d.get("location") or "").strip()
    if country.lower() in ["india", "in"] or is_india_opportunity(loc) or extract_country_from_location(loc) == "India":
        k = compute_dedup_key(d.get("company", ""), d.get("title", ""), d.get("location", ""), d.get("job_type", "full_time"), d.get("is_remote", False))
        if k not in seen:
            seen.add(k)
            unique_docs.append(d)

print(f"Loaded {len(unique_docs)} unique docs.")

total = len(unique_docs)
fields = ["Salary", "Stipend", "Skills", "Experience", "Qualifications", "Responsibilities", "Apply URL"]
stats = {f: {"known": 0, "unknown": 0, "invalid": 0} for f in fields}

for d in unique_docs:
    comp = evaluate_opportunity_completeness(d)
    
    # Salary / Stipend
    if comp.is_salary_disclosed:
        stats["Salary"]["known"] += 1
    else:
        stats["Salary"]["unknown"] += 1
        
    if d.get("job_type") == "internship":
        if comp.is_stipend_disclosed:
            stats["Stipend"]["known"] += 1
        else:
            stats["Stipend"]["unknown"] += 1
    else:
        stats["Stipend"]["unknown"] += 1
        
    # Skills
    if comp.is_skills_disclosed:
        stats["Skills"]["known"] += 1
    else:
        stats["Skills"]["unknown"] += 1
        
    # Experience
    if comp.is_experience_disclosed:
        stats["Experience"]["known"] += 1
    else:
        stats["Experience"]["unknown"] += 1
        
    # Qualifications
    if comp.is_qualifications_disclosed:
        stats["Qualifications"]["known"] += 1
    else:
        stats["Qualifications"]["unknown"] += 1
        
    # Responsibilities
    if comp.is_responsibilities_disclosed:
        stats["Responsibilities"]["known"] += 1
    else:
        stats["Responsibilities"]["unknown"] += 1
        
    # Apply URL
    apply_url = d.get("apply_url") or d.get("application_url")
    if apply_url and apply_url.startswith("http"):
        stats["Apply URL"]["known"] += 1
    else:
        stats["Apply URL"]["invalid"] += 1

print("\n--- INFORMATION COVERAGE TABLE ---")
print(f"{'Field':<20} | {'Known':<10} | {'Unknown/Undisclosed':<20} | {'Invalid':<10}")
print("-" * 70)
for f in fields:
    k = stats[f]["known"]
    u = stats[f]["unknown"]
    inv = stats[f]["invalid"]
    print(f"{f:<20} | {k:<10} | {u:<20} | {inv:<10}")
