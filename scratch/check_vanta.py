import json
import os

path = r'C:\Users\vinny\.gemini\antigravity-ide\brain\c36fb59b-6dca-423b-9993-7283ec005f13\.system_generated\steps\1973\content.md'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    idx = text.find('{"jobs":')
    if idx != -1:
        data = json.loads(text[idx:])
        jobs = data.get('jobs', [])
        print(f"Vanta: {len(jobs)} total jobs")
        india = [j for j in jobs if 'india' in json.dumps(j.get('address', {})).lower() or 'india' in j.get('location', '').lower() or 'bengaluru' in j.get('location', '').lower()]
        print(f"Vanta India jobs: {len(india)}")
        for j in india:
            print(" -", j.get('title'), "|", j.get('location'))
