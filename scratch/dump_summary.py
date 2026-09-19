import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

data = json.load(open("scratch/scan_587_results.json", encoding="utf-8"))

# Load all docs and find all unique false positive postings
from collections import defaultdict

# Let's inspect the entire list from scan_587_results.json
with open("scratch/scan_587_results.json", "r", encoding="utf-8") as f:
    d = json.load(f)

print(f"Total Records Scanned: {d['total_scanned']}")
print(f"Numeric Salary Matches: {d['numeric_salary_count']}")
print(f"Numeric Stipend Matches: {d['numeric_stipend_count']}")
print(f"Qualitative Matches: {d['qualitative_count']}")
print(f"Genuinely Undisclosed Matches: {d['genuinely_undisclosed_count']}")
print(f"False-Positive Job Postings Screened: {d['false_positive_job_count']}")
print(f"Total False-Positive Mentions Screened: {d['false_positive_mention_count']}")

print("\n--- Provider Breakdown ---")
for prov, stats in d["provider_breakdown"].items():
    print(f"Provider: {prov}")
    for k, v in stats.items():
        print(f"  {k}: {v}")
