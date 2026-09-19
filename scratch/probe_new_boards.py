import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

CANDIDATE_GREENHOUSE = ["swiggy", "razorpay", "urbancompany", "phonepe", "zerodha", "juspay", "zepto", "browserstack", "hasura"]
CANDIDATE_LEVER = ["slice", "jupiter", "cleartax", "curefit", "dream11", "mpl", "udaan", "khatabook", "mplgaming"]

print("=== PROBING GREENHOUSE BOARDS ===")
for b in CANDIDATE_GREENHOUSE:
    url = f"https://boards-api.greenhouse.io/v1/boards/{b}/jobs"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RoleRadar/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            jobs = data.get("jobs", [])
            india_jobs = [j for j in jobs if "india" in (j.get("location", {}).get("name", "")).lower()]
            print(f"Greenhouse [{b}]: {len(jobs)} total jobs, {len(india_jobs)} India jobs")
    except Exception as e:
        print(f"Greenhouse [{b}]: Not accessible ({e})")

print("\n=== PROBING LEVER BOARDS ===")
for b in CANDIDATE_LEVER:
    url = f"https://api.lever.co/v0/postings/{b}?mode=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RoleRadar/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            india_jobs = [j for j in data if "india" in (j.get("categories", {}).get("location", "")).lower() or "bengaluru" in (j.get("categories", {}).get("location", "")).lower()]
            print(f"Lever [{b}]: {len(data)} total jobs, {len(india_jobs)} India jobs")
    except Exception as e:
        print(f"Lever [{b}]: Not accessible ({e})")
