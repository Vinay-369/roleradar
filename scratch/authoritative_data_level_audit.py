import asyncio
import json
import re
from urllib.parse import urlparse
from motor.motor_asyncio import AsyncIOMotorClient

# Connect to MongoDB
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "roleradar"

def is_valid_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    parsed = urlparse(url)
    return bool(parsed.netloc and parsed.scheme)

def is_generic_career_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    path = parsed.path.rstrip("/").lower()
    # Typical generic career paths without requisition IDs
    if path in ["/careers", "/jobs", "/career", "/join-us", "/work-with-us", ""]:
        return True
    return False

async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    coll = db["jobs"]

    live_sources = ["smartrecruiters", "lever", "greenhouse"]

    # 1. AUDIT ALL LIVE DIRECT OPPORTUNITIES
    # Query: verification_status == "VERIFIED_ACTIVE" and source in live_sources
    query = {
        "verification_status": "VERIFIED_ACTIVE",
        "source": {"$in": live_sources}
    }

    cursor = coll.find(query)
    all_jobs = await cursor.to_list(length=None)

    total_count = len(all_jobs)

    provider_stats = {}
    for src in live_sources:
        provider_stats[src] = {
            "total": 0,
            "valid_url": 0,
            "missing_url": 0,
            "empty_url": 0,
            "invalid_malformed_url": 0,
            "is_direct_apply_true": 0,
            "is_direct_apply_false": 0,
            "generic_career_url": 0,
            "urls": []
        }

    overall_urls = []
    
    for job in all_jobs:
        src = job.get("source")
        stats = provider_stats[src]
        stats["total"] += 1

        apply_url = job.get("apply_url")
        is_direct = job.get("is_direct_apply", False)

        if is_direct:
            stats["is_direct_apply_true"] += 1
        else:
            stats["is_direct_apply_false"] += 1

        if apply_url is None:
            stats["missing_url"] += 1
        elif isinstance(apply_url, str) and apply_url.strip() == "":
            stats["empty_url"] += 1
        elif not is_valid_url(apply_url):
            stats["invalid_malformed_url"] += 1
        else:
            stats["valid_url"] += 1
            url_clean = apply_url.strip()
            stats["urls"].append(url_clean)
            overall_urls.append(url_clean)

            if is_generic_career_url(url_clean):
                stats["generic_career_url"] += 1

    # Check duplicates
    url_counts = {}
    for u in overall_urls:
        url_counts[u] = url_counts.get(u, 0) + 1
    
    duplicates = {u: count for u, count in url_counts.items() if count > 1}

    # Summary numbers
    total_valid = sum(p["valid_url"] for p in provider_stats.values())
    total_missing = sum(p["missing_url"] for p in provider_stats.values())
    total_empty = sum(p["empty_url"] for p in provider_stats.values())
    total_invalid = sum(p["invalid_malformed_url"] for p in provider_stats.values())
    total_direct_true = sum(p["is_direct_apply_true"] for p in provider_stats.values())
    total_direct_false = sum(p["is_direct_apply_false"] for p in provider_stats.values())
    total_generic = sum(p["generic_career_url"] for p in provider_stats.values())

    coverage_pct = (total_valid / total_count * 100) if total_count > 0 else 0

    results = {
        "overall": {
            "total_live_direct_opportunities": total_count,
            "total_valid_url": total_valid,
            "total_missing_url": total_missing,
            "total_empty_url": total_empty,
            "total_invalid_malformed_url": total_invalid,
            "total_is_direct_apply_true": total_direct_true,
            "total_is_direct_apply_false": total_direct_false,
            "total_generic_career_urls": total_generic,
            "coverage_pct": round(coverage_pct, 2),
            "duplicate_url_count": len(duplicates),
            "duplicates": duplicates
        },
        "by_provider": {
            src: {
                "total": p["total"],
                "valid_url": p["valid_url"],
                "missing_url": p["missing_url"],
                "empty_url": p["empty_url"],
                "invalid_malformed_url": p["invalid_malformed_url"],
                "is_direct_apply_true": p["is_direct_apply_true"],
                "is_direct_apply_false": p["is_direct_apply_false"],
                "generic_career_url": p["generic_career_url"],
                "coverage_pct": round((p["valid_url"] / p["total"] * 100) if p["total"] > 0 else 0, 2)
            }
            for src, p in provider_stats.items()
        }
    }

    # Print out summary JSON
    print("=== AUDIT RESULTS ===")
    print(json.dumps(results, indent=2))

    # Also inspect Bosch Mobile and Bosch Hardware
    bosch_mobile = await coll.find_one({"id": "smartrecruiters_boschgroup_744000147203758"})
    bosch_hardware = await coll.find_one({"id": "smartrecruiters_boschgroup_744000147209508"})

    print("\n=== BOSCH MOBILE RECORD ===")
    if bosch_mobile:
        print("Title:", bosch_mobile.get("title"))
        print("Apply URL:", bosch_mobile.get("apply_url"))
        print("is_direct_apply:", bosch_mobile.get("is_direct_apply"))
        print("verification_status:", bosch_mobile.get("verification_status"))
        print("Experience:", bosch_mobile.get("experience_min"), "to", bosch_mobile.get("experience_max"))
        print("Location:", bosch_mobile.get("location"))
        print("Qualifications:", bosch_mobile.get("qualifications"))
        print("Skills Required:", bosch_mobile.get("skills_required"))
        print("Skills Nice to Have:", bosch_mobile.get("skills_nice_to_have"))
        print("Responsibilities Count:", len(bosch_mobile.get("responsibilities", [])))
    else:
        print("NOT FOUND")

    print("\n=== BOSCH HARDWARE RECORD ===")
    if bosch_hardware:
        print("Title:", bosch_hardware.get("title"))
        print("Apply URL:", bosch_hardware.get("apply_url"))
        print("is_direct_apply:", bosch_hardware.get("is_direct_apply"))
        print("verification_status:", bosch_hardware.get("verification_status"))
        print("Experience:", bosch_hardware.get("experience_min"), "to", bosch_hardware.get("experience_max"))
        print("Location:", bosch_hardware.get("location"))
        print("Qualifications:", bosch_hardware.get("qualifications"))
        print("Skills Required:", bosch_hardware.get("skills_required"))
        print("Skills Nice to Have:", bosch_hardware.get("skills_nice_to_have"))
        print("Responsibilities Count:", len(bosch_hardware.get("responsibilities", [])))
    else:
        print("NOT FOUND")

    # Sample one from each provider for lineage
    print("\n=== SAMPLE FOR LINEAGE ===")
    for src in live_sources:
        sample = await coll.find_one({"source": src, "verification_status": "VERIFIED_ACTIVE"})
        if sample:
            print(f"Provider: {src}")
            print(f"  ID: {sample.get('id')}")
            print(f"  Title: {sample.get('title')}")
            print(f"  Company: {sample.get('company')}")
            print(f"  apply_url: {sample.get('apply_url')}")
            print(f"  is_direct_apply: {sample.get('is_direct_apply')}")
            print(f"  url_type: {sample.get('url_type')}")
            print(f"  source_url: {sample.get('source_url')}")

if __name__ == "__main__":
    asyncio.run(main())
