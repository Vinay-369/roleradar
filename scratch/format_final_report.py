import json

d = json.load(open("scratch/phase17_full_report_metrics.json", encoding="utf-8"))
audit = json.load(open("scratch/phase17_audit_data.json", encoding="utf-8"))

print("==================================================")
print("PROVIDER INVENTORY")
print("==================================================")
print("Provider | Raw | Normalized | India | Active | Relevant | Valid Apply | Primary | Secondary | Rejected")
print(":--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---")
for p, m in audit["provider_metrics"].items():
    print(f"{p} | {m['raw']} | {m['normalized']} | {m['india']} | {m['active']} | {m['relevant']} | {m['valid_apply']} | {m['primary']} | {m['secondary']} | {m['rejected']}")

print("\n==================================================")
print("REJECTION FUNNEL")
print("==================================================")
print("Stage | Count | Percentage Lost")
print(":--- | :--- | :---")
# Raw Total in Direct ATS: 2747
stages = [
    ("Provider Ingested (Direct ATS)", 2747, "0.0% (Baseline)"),
    ("Normalized (Title & Company)", 2747, "0.0%"),
    ("Deduplicated Requisitions", 2745, "0.07% (2 duplicate postings)"),
    ("India Geography Classified", 590, "78.51% (2,155 foreign postings)"),
    ("Active Requisitions Verified", 588, "0.34% (2 closed requisitions)"),
    ("Relevant Opportunities (>=50 char JD)", 587, "0.17% (1 empty Paytm stub)"),
    ("Valid Direct Apply Path", 587, "0.0%"),
    ("Ranked Primary Recommendations", 250, "42.59% (Rich documentation)"),
    ("Ranked Secondary Recommendations", 337, "57.41% (Actionable brief documentation)")
]
for s, c, p in stages:
    print(f"{s} | {c} | {p}")

print("\n==================================================")
print("REJECTION REASONS")
print("==================================================")
print("Reason | Count | Percentage")
print(":--- | :--- | :---")
tot_rej = sum(audit["rejection_reasons"].values())
for r, c in sorted(audit["rejection_reasons"].items(), key=lambda x: x[1], reverse=True):
    print(f"{r} | {c} | {c/tot_rej*100:.2f}%")

print("\n==================================================")
print("PROVIDER QUALITY")
print("==================================================")
print("Provider | Indian Inventory | Relevant | Direct Apply % | Duplicate % | Role Coverage | Internship Coverage")
print(":--- | :--- | :--- | :--- | :--- | :--- | :---")
for p, q in d["provider_quality"].items():
    print(f"{p} | {q['indian_inventory']} | {q['relevant']} | {q['direct_apply_pct']}% | {q['duplicate_pct']}% | {q['role_coverage']} roles | {q['internship_coverage']} internships")

print("\n==================================================")
print("INFORMATION COVERAGE")
print("==================================================")
print("Field | Known | Unknown | Invalid/Rejected")
print(":--- | :--- | :--- | :---")
for field, counts in d["info_coverage"].items():
    print(f"{field} | {counts['known']} | {counts['unknown']} | {counts['invalid']}")

print("\n==================================================")
print("INTERNSHIP COVERAGE")
print("==================================================")
print("Role | Active India | Relevant | Primary | Secondary")
print(":--- | :--- | :--- | :--- | :---")
for r, m in d["intern_role_metrics"].items():
    if m["active_india"] > 0:
        print(f"{r} | {m['active_india']} | {m['relevant']} | {m['primary']} | {m['secondary']}")

print("\n==================================================")
print("ROLE COVERAGE (ACTIVE ROLES SUMMARY)")
print("==================================================")
print("Role | Active India | Relevant | Valid Apply | Primary | Secondary | Rejected")
print(":--- | :--- | :--- | :--- | :--- | :--- | :---")
for r, m in sorted(d["role_metrics"].items(), key=lambda x: x[1]["active_india"], reverse=True):
    if m["active_india"] > 0:
        print(f"{r} | {m['active_india']} | {m['relevant']} | {m['valid_apply']} | {m['primary']} | {m['secondary']} | {m['rejected']}")
