import sys
sys.path.insert(0, 'backend')
import json
from app.modules.jobs.ashby_provider import AshbyJobProvider
from app.modules.jobs.relevance_engine import is_india_opportunity

p = AshbyJobProvider()
jobs = p.fetch_board_jobs('elevenlabs')
print(f"Total elevenlabs jobs: {len(jobs)}")
for j in jobs:
    title = j.get('title', '')
    loc = j.get('location', '')
    sec = j.get('secondaryLocations', [])
    addr = j.get('address', {})
    
    sec_names = [s.get('location', '') for s in sec]
    country = addr.get('postalAddress', {}).get('addressCountry', '')
    
    # Check normalized is_india
    norm = p.normalize_job(j, 'elevenlabs', 'ElevenLabs')
    if norm and norm.get('is_india_opportunity'):
        print("--- MATCH ---")
        print(f"Title: {title}")
        print(f"Primary Loc: {loc}")
        print(f"Sec Locs: {sec_names}")
        print(f"Country: {country}")
        print(f"Normalized Loc: {norm.get('location')}")
