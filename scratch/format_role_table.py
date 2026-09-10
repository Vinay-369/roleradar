import json

with open("scratch/phase17_correction_report_authoritative.json", "r", encoding="utf-8") as f:
    data = json.load(f)

matrix = data["role_matrix"]
roles_sorted = sorted(matrix.keys())

with open("scratch/role_coverage_table.md", "w", encoding="utf-8") as f:
    f.write("| Canonical Role | Active India | Relevant | Valid Apply | Primary | Secondary | Full-Time | Internships |\n")
    f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
    for r in roles_sorted:
        m = matrix[r]
        if m["active_india"] > 0:
            f.write(f"| **{r}** | **{m['active_india']}** | **{m['relevant']}** | **{m['valid_apply']}** | **{m['primary']}** | **{m['secondary']}** | **{m['full_time']}** | **{m['internships']}** |\n")
        else:
            f.write(f"| {r} | 0 | 0 | 0 | 0 | 0 | 0 | 0 |\n")

print("Wrote role coverage table to scratch/role_coverage_table.md")
