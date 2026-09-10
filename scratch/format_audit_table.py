import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

rows = json.load(open("scratch/forensic_salary_audit_results.json", encoding="utf-8"))

print("| # | Canonical ID | Prov | Company | Role Title | Type | Raw ATS API | Desc / Text Comp | Mongo DB Stored | API (JobOut) | UI Detail Presentation | Class |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|")
for i, r in enumerate(rows, 1):
    cid = r["id"]
    prov = r["provider"]
    comp = r["company"][:12]
    title = r["title"][:22]
    opp_type = r["type"]
    api_raw = "None" if r["raw_api_comp"] is None else str(r["raw_api_comp"])[:14]
    disc = (r["numeric_desc"] or r["qual_desc"] or ["Undisclosed"])[0]
    disc = disc[:25]
    mongo = str(r["mongo"])[:15]
    api_txt = (r["api"][5] or "None")[:22] if len(r["api"]) > 5 else "None"
    ui = r["ui_detail"][:26]
    cls_name = r["classification"]
    print(f"| {i} | `{cid}` | {prov} | {comp} | {title} | {opp_type} | {api_raw} | {disc} | {mongo} | {api_txt} | {ui} | **{cls_name}** |")
