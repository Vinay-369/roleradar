import json

with open("scratch/phase17_correction_report_authoritative.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Authoritative Totals:")
print(json.dumps(data["authoritative_totals"], indent=2))

print("\nProvider Stats:")
print(json.dumps(data["provider_stats"], indent=2))

print("\nSpecialized Audit:")
print(json.dumps(data["specialized_audit"], indent=2))
