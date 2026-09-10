import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
sys.stdout.reconfigure(encoding="utf-8")
import json
import re
from collections import Counter
from app.modules.learning.role_taxonomy import ROLE_TAXONOMY, resolve_role

with open(r"c:\VINAY\roleradar\scratch\all_383_specialized_dump.json", encoding="utf-8") as f:
    items = json.load(f)

print(f"Auditing all {len(items)} specialized records...")

canonical_titles = {v.canonical_role: k for k, v in ROLE_TAXONOMY.items()}

# We will categorize each record into A, B, C, D
# A: Genuinely specialized (e.g. VLSI, semiconductor, automotive mechanical, collections, insurance, legal M&A)
# B: Clearly mappable to existing canonical role with solid evidence
# C: Ambiguous / insufficient evidence (e.g. "Team leader", "Portfolio Specialist")
# D: Parser/taxonomy failure (e.g. Network Engineer, Application Security, punctuation/regex issue)

audited_results = []

for item in items:
    t = item["title"]
    c = item["company"]
    desc = item["desc_snippet"].lower()
    t_clean = re.sub(r"[–—]", "-", t).strip()
    
    # Analyze role candidate
    target_role = None
    category = None
    evidence = None

    # Check for D (Parser/taxonomy punctuation/delimiter failure)
    # 1. Network Engineer
    if re.search(r"\bnetwork engineer\b", t_clean, re.I):
        category = "D"
        target_role = "Network Engineer" if "Network Engineer" in canonical_titles else "Cloud Engineer"
        evidence = "Title explicitly specifies Network Engineer; blocked by seniority prefix or missing exact alias"

    # 2. Application Security
    elif re.search(r"application security|appsec", t_clean, re.I):
        category = "D"
        target_role = "Security Engineer"
        evidence = "Title explicitly specifies Application Security; blocked by delimiter 'Manager- Application Security'"

    # 3. Software Engineer variations (e.g. Senior Software Engineer(AI/ML), Dot Net Software Developer, Staff Engineer)
    elif "software engineer(ai/ml)" in t_clean.lower():
        category = "B"
        target_role = "Machine Learning Engineer"
        evidence = "Title explicitly specifies Software Engineer(AI/ML) working on machine learning models"
    elif "dot net software developer" in t_clean.lower() or ".net software developer" in t_clean.lower():
        category = "B"
        target_role = "Software Engineer"
        evidence = "Title explicitly specifies .NET Software Developer"
    elif "mean stack developer" in t_clean.lower():
        category = "B"
        target_role = "Full Stack Developer"
        evidence = "MEAN Stack (MongoDB, Express, Angular, Node) is canonical Full Stack development"
    elif "php developer" in t_clean.lower():
        category = "B"
        target_role = "Backend Developer"
        evidence = "PHP server-side language is canonical Backend development"
    elif "node js developer" in t_clean.lower() or "nodejs developer" in t_clean.lower():
        category = "B"
        target_role = "Backend Developer"
        evidence = "Node.js runtime server-side development is canonical Backend development"
    elif "business analyst- paytm ads" in t_clean.lower() or (re.search(r"\bbusiness analyst\b", t_clean, re.I) and "ads" in t_clean.lower()):
        category = "B"
        target_role = "Data Analyst"
        evidence = "Business Analyst for Ads domain focusing on performance data and analytics"
    elif "lead - advanced analytics" in t_clean.lower():
        category = "B"
        target_role = "Data Analyst"
        evidence = "Advanced Analytics lead is canonical Data Analyst / Advanced Data Analytics"
    elif "enterprise account executive" in t_clean.lower():
        category = "B"
        target_role = "Sales Executive"
        evidence = "Account Executive is industry standard for B2B Sales Executive"
    elif "enterprise solutions consultant" in t_clean.lower():
        category = "B"
        target_role = "Technology Consultant"
        evidence = "Enterprise Solutions Consultant is canonical Technology Consultant"
    elif "interactive art director" in t_clean.lower():
        category = "B"
        target_role = "Creative Director"
        evidence = "Art Director is canonical Creative Director / Design Director"
    elif "content writer" in t_clean.lower() or "proof reader" in t_clean.lower() or "copy - editor" in t_clean.lower():
        category = "B"
        target_role = "Copywriter"
        evidence = "Content writing, copy editing, and proofreading are canonical Copywriter domain"
    elif "business development & strategic partnerships" in t_clean.lower() or "business development & partnerships" in t_clean.lower():
        category = "B"
        target_role = "Business Development Executive"
        evidence = "Business Development and Strategic Partnerships is canonical Business Development Executive"
    elif re.search(r"\br&d engineer \(c\+\+\)", t_clean, re.I):
        category = "B"
        target_role = "Software Engineer"
        evidence = "R&D Engineer in C++ for gaming engine is canonical systems Software Engineer"
    elif "embtesting" in t_clean.lower():
        category = "B"
        target_role = "QA / Test Engineer"
        evidence = "ECT3_EmbTesting represents Embedded Software Testing QA role"
    
    # Check for Genuinely Specialized roles (A)
    elif any(kw in t_clean.lower() for kw in [
        "vlsi", "asic", "semiconductor", "fabrication", "fpga", "soc",
        "collections", "lending collections", "procurement", "accounts payable",
        "motor insurance", "controllership", "real estate", "manufacturing operations",
        "magnet localization", "m&a", "mergers", "facilities", "revenue operations",
        "deal desk", "underwriting", "recovery", "wealth", "treasury", "tax",
        "last mile", "nbfc", "plant head", "process engineer", "maintenance",
        "warehouse", "chassis", "powertrain", "hydraulic", "stamping", "sheet north"
    ]):
        category = "A"
        evidence = "Domain-specific specialized role (semiconductor/manufacturing/finance/collections) with no matching canonical profile"

    # Check for Ambiguous (C)
    elif any(kw in t_clean.lower() for kw in [
        "team leader", "cluster head", "deputy manager", "assistant manager", "associate director",
        "general manager", "staff engineer i", "staff engineer 1", "portfolio specialist",
        "lead - on deck", "growth and business", "office manager", "supervisor", "operations group head"
    ]):
        category = "C"
        evidence = "Broad corporate title or level indicator without discriminative role domain keywords"
    else:
        # Default assessment
        category = "A"
        evidence = "Specialized requisition requiring distinct specialized domain expertise"

    audited_results.append({
        "id": item["id"],
        "title": t,
        "company": c,
        "category": category,
        "target_role": target_role,
        "evidence": evidence
    })

cat_counts = Counter(r["category"] for r in audited_results)
print("\n--- CATEGORIZATION SUMMARY ---")
print(f"Category A (Genuinely Specialized): {cat_counts['A']}")
print(f"Category B (Clearly Mappable with Evidence): {cat_counts['B']}")
print(f"Category C (Ambiguous / Insufficient Evidence): {cat_counts['C']}")
print(f"Category D (Parser / Taxonomy Gap): {cat_counts['D']}")

print("\n--- PROPOSED REMAPPINGS (Categories B & D) ---")
remapped = [r for r in audited_results if r["category"] in ("B", "D")]
remap_counts = Counter(f"{r['title']} -> {r['target_role']} (from {r['company']})" for r in remapped)
for r_str, count in remap_counts.most_common():
    print(f"  [{count}x] {r_str}")

with open(r"c:\VINAY\roleradar\scratch\audit_383_categorized.json", "w", encoding="utf-8") as f:
    json.dump(audited_results, f, indent=2)

print("\nSaved categorized audit to scratch/audit_383_categorized.json")
