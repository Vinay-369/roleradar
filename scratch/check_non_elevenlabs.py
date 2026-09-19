from pymongo import MongoClient
c = MongoClient('mongodb://127.0.0.1:27017')
db = c['roleradar']
jobs = list(db.jobs.find({'source': 'ashby', 'is_india_opportunity': True, 'company': {'$ne': 'Elevenlabs'}}))
for j in jobs:
    print(f"{j.get('company')}: {j.get('title')} | Loc: {j.get('location')}")
