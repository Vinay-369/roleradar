import httpx
import json

def test_api():
    with httpx.Client(base_url="http://localhost:8000/api", timeout=10.0) as client:
        # 1. Jobs
        r_jobs = client.get("/jobs", params={"region": "india", "limit": 5})
        j_data = r_jobs.json()
        print(f"Jobs endpoint: status {r_jobs.status_code}, count {len(j_data.get('items', []))}, total {j_data.get('total')}")

        # 2. Internships
        r_interns = client.get("/jobs", params={"region": "india", "job_type": "internship", "limit": 5})
        i_data = r_interns.json()
        print(f"Internships endpoint: status {r_interns.status_code}, count {len(i_data.get('items', []))}, total {i_data.get('total')}")

        # 3. Cred Job Detail
        r_cred = client.get("/jobs/lever_cred_fa6c100a-0fe0-4892-a8a3-8d2169d5005e")
        if r_cred.status_code == 200:
            cdata = r_cred.json()
            print(f"Cred Job: {cdata.get('title')}, salary_disclosed: {cdata.get('salary_disclosed')}, salary_min: {cdata.get('salary_min')}")
        else:
            print(f"Cred Job: status {r_cred.status_code}")

        # 4. Hydrated SmartRecruiters Job Detail
        r_sr = client.get("/jobs/smartrecruiters_boschgroup_744000147416769")
        if r_sr.status_code == 200:
            sdata = r_sr.json()
            print(f"Hydrated SR Job: {sdata.get('title')}, desc_len: {len(sdata.get('description') or '')}, resps: {len(sdata.get('responsibilities') or [])}")
        else:
            print(f"Hydrated SR Job: status {r_sr.status_code}")

        # 5. Canonical Roles
        r_roles = client.get("/learning/roles")
        print(f"Canonical roles endpoint: status {r_roles.status_code}, total roles {len(r_roles.json())}")

if __name__ == "__main__":
    test_api()
