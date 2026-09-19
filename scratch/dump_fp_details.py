import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

data = json.load(open("scratch/scan_587_results.json", encoding="utf-8"))
fps = data["false_positive_examples"]

print(f"Total Unique Postings with False-Positive Financial/Metric Mentions: {len(fps)}")
for i, fp in enumerate(fps, 1):
    print(f"\n--- [{i}] Opportunity ID: {fp['id']} ---")
    print(f"Company: {fp['company']} | Title: {fp['title']}")
    print(f"Matched Money / Number Token: {fp['matched_money']}")
    print(f"Safeguard Pattern: {fp['fp_reason']}")
    print(f"Exact Source Context:\n  \"{fp['snippet']}\"")
