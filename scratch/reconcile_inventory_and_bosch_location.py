import asyncio
import json
import sys
sys.path.insert(0, ".")

from motor.motor_asyncio import AsyncIOMotorClient
from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location
from app.modules.jobs.smartrecruiters_provider import SmartRecruitersJobProvider

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]
    coll = db["jobs"]

    print("==================================================")
    print("1. BOSCH MOBILE LOCATION DEEP INVESTIGATION")
    print("==================================================")
    job_id = "smartrecruiters_boschgroup_744000147203758"
    doc = await coll.find_one({"id": job_id})
    if doc:
        print("MongoDB Document Location Fields:")
        print(f"  location: {doc.get('location')}")
        print(f"  city: {doc.get('city')}")
        print(f"  region: {doc.get('region')}")
        print(f"  country: {doc.get('country')}")
        print(f"  address: {doc.get('address')}")
    else:
        print("Document not found in MongoDB!")

    sr = SmartRecruitersJobProvider()
    raw = await sr.fetch_specific_opening("BoschGroup", "744000147203758")
    if raw:
        print("\nRaw SmartRecruiters API Top-Level Location:")
        print(json.dumps(raw.get("location"), indent=2))
        print(f"\nRaw postingUrl: {raw.get('postingUrl')}")
        print(f"Raw applyUrl: {raw.get('applyUrl')}")
        print(f"Raw customField: {raw.get('customField')}")
        
        # Check text in sections for mentions of Bengaluru / Bangalore / Coimbatore
        jobAd = raw.get("jobAd", {})
        sections = jobAd.get("sections", {})
        print("\nScanning raw jobAd text for location keywords:")
        for sname, sdata in sections.items():
            text = sdata.get("text", "")
            has_blr = "bengaluru" in text.lower() or "bangalore" in text.lower()
            has_cbe = "coimbatore" in text.lower()
            print(f"  Section '{sname}': contains 'Bengaluru/Bangalore': {has_blr}, contains 'Coimbatore': {has_cbe}")
            if has_blr:
                # show snippet
                idx = text.lower().find("bangalore") if "bangalore" in text.lower() else text.lower().find("bengaluru")
                print(f"    Snippet: {text[max(0, idx-50):min(len(text), idx+100)]}")
            if has_cbe:
                idx = text.lower().find("coimbatore")
                print(f"    Snippet: {text[max(0, idx-50):min(len(text), idx+100)]}")

    print("\n==================================================")
    print("2. INVENTORY RECONCILIATION")
    print("==================================================")
    live_sources = ["smartrecruiters", "lever", "greenhouse"]
    cursor = coll.find({
        "verification_status": "VERIFIED_ACTIVE",
        "source": {"$in": live_sources}
    })
    all_jobs = await cursor.to_list(length=None)
    total_active_ats = len(all_jobs)

    # Let's check how India is classified
    # 1. Using doc.get('country') == 'India' or doc.get('country') == 'in'
    # 2. Using is_indian_location(doc.get('location'))
    # 3. Using extract_country_from_location(doc.get('location')) == 'India'
    india_count_by_flag = 0
    india_count_by_loc_func = 0
    india_count_by_extracted_country = 0

    provider_breakdown = {
        "smartrecruiters": {"total": 0, "india": 0, "non_india": 0},
        "lever": {"total": 0, "india": 0, "non_india": 0},
        "greenhouse": {"total": 0, "india": 0, "non_india": 0},
    }

    country_distribution = {}

    for job in all_jobs:
        src = job.get("source")
        loc = job.get("location") or ""
        country = job.get("country") or ""
        
        provider_breakdown[src]["total"] += 1

        is_ind_loc = is_india_opportunity(loc)
        ext_country = extract_country_from_location(loc)
        
        is_india = (country.lower() in ["india", "in"]) or is_ind_loc or (ext_country == "India")

        if is_india:
            provider_breakdown[src]["india"] += 1
        else:
            provider_breakdown[src]["non_india"] += 1

        # Track countries
        c_key = country or ext_country or "Unknown"
        country_distribution[c_key] = country_distribution.get(c_key, 0) + 1

    total_india = sum(p["india"] for p in provider_breakdown.values())
    total_non_india = sum(p["non_india"] for p in provider_breakdown.values())

    print(f"TOTAL VERIFIED_ACTIVE ATS: {total_active_ats}")
    print(f"TOTAL INDIA VERIFIED_ACTIVE: {total_india}")
    print(f"TOTAL NON-INDIA VERIFIED_ACTIVE: {total_non_india}")
    print(f"Reconciliation check: {total_india} + {total_non_india} = {total_india + total_non_india} == {total_active_ats}")

    print("\nProvider Breakdown of INDIA VERIFIED_ACTIVE:")
    for src, p in provider_breakdown.items():
        print(f"  {src}: {p['india']} India / {p['total']} Total (Non-India: {p['non_india']})")

    # Check why earlier audit reported 587
    print("\nLet's check if 587 corresponds to a specific subset:")
    # e.g., only curated? only smartrecruiters? only specific query?
    curated_india = await coll.count_documents({"source": "curated"})
    print(f"Curated jobs count: {curated_india}")
    
    # Check jobs with country="India" exact in DB
    exact_india_in_db = await coll.count_documents({
        "verification_status": "VERIFIED_ACTIVE",
        "source": {"$in": live_sources},
        "country": "India"
    })
    print(f"Exact country == 'India' in DB: {exact_india_in_db}")

    print("\n--- EXACT MONGO QUERY (country == 'India') BREAKDOWN ---")
    for src in live_sources:
        s_ind = await coll.count_documents({
            "verification_status": "VERIFIED_ACTIVE",
            "source": src,
            "country": "India"
        })
        s_tot = await coll.count_documents({
            "verification_status": "VERIFIED_ACTIVE",
            "source": src
        })
        print(f"  {src}: {s_ind} India / {s_tot} Total (Non-India: {s_tot - s_ind})")

    exact_in_code_in_db = await coll.count_documents({
        "verification_status": "VERIFIED_ACTIVE",
        "source": {"$in": live_sources},
        "country": {"$in": ["in", "IN"]}
    })
    print(f"Exact country in ['in', 'IN'] in DB: {exact_in_code_in_db}")

    print("\nCountry Distribution (top 15):")
    sorted_countries = sorted(country_distribution.items(), key=lambda x: x[1], reverse=True)[:15]
    for c, count in sorted_countries:
        print(f"  {c}: {count}")

if __name__ == "__main__":
    asyncio.run(main())
