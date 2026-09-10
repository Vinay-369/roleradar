import asyncio
import httpx
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.modules.learning.role_taxonomy import resolve_role
from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location
from app.modules.jobs.deduplication import compute_dedup_key
from collections import Counter, defaultdict

candidate_boards = {
    "greenhouse": [
        ("okta", "Okta"),
        ("purestorage", "Pure Storage"),
        ("gitlab", "GitLab"),
        ("rubrik", "Rubrik"),
        ("elastic", "Elastic"),
        ("twilio", "Twilio"),
        ("mongodb", "MongoDB"),
        ("newrelic", "New Relic"),
        ("samsara", "Samsara"),
        ("yugabyte", "Yugabyte"),
        ("cockroachlabs", "Cockroach Labs"),
    ],
    "lever": [
        ("zeta", "Zeta"),
        ("pocketfm", "Pocket FM"),
    ],
    "smartrecruiters": [
        ("Continental", "Continental AG"),
    ]
}

async def fetch_gh(client, token, company):
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    try:
        r = await client.get(url, timeout=12.0)
        if r.status_code != 200:
            return []
        data = r.json()
        jobs = []
        for j in data.get("jobs", []):
            loc_name = (j.get("location", {}) or {}).get("name") or ""
            if not (is_india_opportunity(loc_name) or extract_country_from_location(loc_name) == "India"):
                continue
            title = (j.get("title") or "").strip()
            desc = j.get("content") or ""
            apply_url = j.get("absolute_url") or f"https://boards.greenhouse.io/{token}/jobs/{j.get('id')}"
            is_intern = "intern" in title.lower()
            jobs.append({
                "source": "greenhouse",
                "source_board": token,
                "company": company,
                "title": title,
                "location": loc_name,
                "country": "India",
                "apply_url": apply_url,
                "description": desc,
                "job_type": "internship" if is_intern else "full_time",
                "raw_id": f"gh_{token}_{j.get('id')}",
            })
        return jobs
    except Exception:
        return []

async def fetch_lever(client, token, company):
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    try:
        r = await client.get(url, timeout=12.0)
        if r.status_code != 200:
            return []
        data = r.json()
        jobs = []
        for j in data:
            loc = (j.get("categories", {}) or {}).get("location") or ""
            if not (is_india_opportunity(loc) or extract_country_from_location(loc) == "India"):
                continue
            title = (j.get("text") or "").strip()
            desc = j.get("description") or j.get("descriptionPlain") or ""
            apply_url = j.get("applyUrl") or j.get("hostedUrl") or ""
            is_intern = "intern" in title.lower() or (j.get("categories", {}).get("commitment") or "").lower() == "intern"
            jobs.append({
                "source": "lever",
                "source_board": token,
                "company": company,
                "title": title,
                "location": loc,
                "country": "India",
                "apply_url": apply_url,
                "description": desc,
                "job_type": "internship" if is_intern else "full_time",
                "raw_id": f"lever_{token}_{j.get('id')}",
            })
        return jobs
    except Exception:
        return []

async def fetch_sr(client, token, company):
    url = f"https://api.smartrecruiters.com/v1/companies/{token}/postings?country=in&limit=100"
    try:
        r = await client.get(url, timeout=12.0)
        if r.status_code != 200:
            return []
        data = r.json()
        jobs = []
        for j in data.get("content", []):
            title = (j.get("name") or "").strip()
            loc_data = j.get("location") or {}
            city = loc_data.get("city") or ""
            loc = f"{city}, India" if city else "India"
            desc = "" # Will test brief or detailed
            apply_url = f"https://jobs.smartrecruiters.com/{token}/{j.get('id')}"
            is_intern = "intern" in title.lower()
            jobs.append({
                "source": "smartrecruiters",
                "source_board": token,
                "company": company,
                "title": title,
                "location": loc,
                "country": "India",
                "apply_url": apply_url,
                "description": desc,
                "job_type": "internship" if is_intern else "full_time",
                "raw_id": f"sr_{token}_{j.get('id')}",
            })
        return jobs
    except Exception:
        return []

async def main():
    async with httpx.AsyncClient(headers={"User-Agent": "RoleRadar-Evaluation/1.0"}) as client:
        all_candidate_jobs = []

        print("Fetching Greenhouse candidate boards...")
        for token, comp in candidate_boards["greenhouse"]:
            res = await fetch_gh(client, token, comp)
            print(f"  {comp} ({token}): {len(res)} Indian opps")
            all_candidate_jobs.extend(res)

        print("\nFetching Lever candidate boards...")
        for token, comp in candidate_boards["lever"]:
            res = await fetch_lever(client, token, comp)
            print(f"  {comp} ({token}): {len(res)} Indian opps")
            all_candidate_jobs.extend(res)

        print("\nFetching SmartRecruiters candidate boards...")
        for token, comp in candidate_boards["smartrecruiters"]:
            res = await fetch_sr(client, token, comp)
            print(f"  {comp} ({token}): {len(res)} Indian opps")
            all_candidate_jobs.extend(res)

    print(f"\nTotal candidate Indian opportunities fetched: {len(all_candidate_jobs)}")
    
    # Analyze deduplication
    seen = set()
    unique_candidates = []
    for j in all_candidate_jobs:
        k = compute_dedup_key(j["company"], j["title"], j["location"], j["job_type"], False)
        if k not in seen:
            seen.add(k)
            unique_candidates.append(j)

    print(f"Unique candidate opportunities: {len(unique_candidates)} (Duplicates: {len(all_candidate_jobs) - len(unique_candidates)})")

    # Analyze role classifications
    role_counts = Counter()
    unmapped = 0
    internships = []
    freshers = []

    for j in unique_candidates:
        t = j["title"]
        prof, conf, reason = resolve_role(t)
        if prof:
            role_counts[prof.canonical_role] += 1
            j["canonical_role"] = prof.canonical_role
        else:
            unmapped += 1
            j["canonical_role"] = "Specialized Requisition"

        if j["job_type"] == "internship":
            internships.append(j)

        if any(kw in t.lower() for kw in ["fresher", "junior", "graduate", "entry", "associate", "intern", "i", "1"]):
            freshers.append(j)

    print(f"\nRole Coverage Yield:")
    print(f"  Mapped Canonical Roles: {len(role_counts)} distinct roles")
    print(f"  Total mapped: {len(unique_candidates) - unmapped}")
    print(f"  Specialized Requisitions: {unmapped} ({unmapped / len(unique_candidates) * 100:.1f}%)")
    print(f"  Internships: {len(internships)}")
    print(f"  Fresher / Entry-level: {len(freshers)}")

    print("\nTop Mapped Roles:")
    for r, c in role_counts.most_common(15):
        print(f"  {r}: {c}")

    if internships:
        print("\nCandidate Internships Found:")
        for i in internships:
            print(f"  [{i['company']}] '{i['title']}' -> {i.get('canonical_role')}")

if __name__ == "__main__":
    asyncio.run(main())
