import asyncio
import sys
sys.path.insert(0, 'backend')
from pymongo import MongoClient
from app.modules.jobs.ashby_provider import AshbyJobProvider

async def main():
    client = MongoClient('mongodb://127.0.0.1:27017')
    db = client['roleradar']
    jobs = list(db.jobs.find({'source': 'ashby', 'company': 'Elevenlabs'}))
    print(f"Total Elevenlabs jobs in DB: {len(jobs)}")

    p = AshbyJobProvider()
    raw_jobs = await p.fetch_company_openings('elevenlabs')
    raw_by_id = {j.get('id'): j for j in raw_jobs}

    for j in jobs:
        if j.get('is_india_opportunity'):
            source_id = j.get('source_job_id')
            raw = raw_by_id.get(source_id, {})
            title = j.get('title')
            loc = j.get('location')
            raw_sec = [s.get('location') for s in raw.get('secondaryLocations', [])]
            raw_addr = raw.get('address', {})
            postal = raw_addr.get('postalAddress', {}) if raw_addr else {}
            country = postal.get('addressCountry')
            print(f"Title: {title}")
            print(f"  DB Location: {loc}")
            print(f"  Raw Location: {raw.get('location')}")
            print(f"  Raw Postal Country: {country}")
            print(f"  Raw Secondary: {raw_sec}")
            print("-" * 50)

if __name__ == '__main__':
    asyncio.run(main())
