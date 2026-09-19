import json

path = r'C:\Users\vinny\.gemini\antigravity-ide\brain\c36fb59b-6dca-423b-9993-7283ec005f13\.system_generated\steps\1946\content.md'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

target = '{"jobs":'
idx = text.find(target)
if idx != -1:
    data = json.loads(text[idx:])
    print("Total jobs in Ashby sample:", len(data['jobs']))
    first = data['jobs'][0]
    print("\nKeys in job object:")
    for k in first.keys():
        if k not in ('descriptionHtml', 'descriptionPlain'):
            print(f"  {k}: {repr(first[k])[:80]}")
    
    # Check all keys across all jobs
    all_keys = set()
    employment_types = set()
    workplace_types = set()
    for j in data['jobs']:
        all_keys.update(j.keys())
        employment_types.add(j.get('employmentType'))
        workplace_types.add(j.get('workplaceType'))
    print("\nAll unique keys across all jobs:", sorted(list(all_keys)))
    print("Unique employmentTypes:", employment_types)
    print("Unique workplaceTypes:", workplace_types)
else:
    print("Target not found")
