import sys
import httpx

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8000/api"

def run_smoke_test():
    print("=" * 60)
    print("[TEST] ROLERADAR FULL END-TO-END LIVE API SMOKE TEST")
    print("=" * 60)

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Health Check
        r = client.get("/health")
        assert r.status_code == 200, f"Health check failed: {r.status_code}"
        print(f"[OK] 1. Health Endpoint: 200 OK ({r.json()['app']})")

        # 2. Authentication Login
        login_res = client.post("/auth/login", json={"email": "demo@example.com", "password": "Password123!"})
        assert login_res.status_code == 200, f"Login failed: {login_res.status_code}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("[OK] 2. Auth / Login: 200 OK (JWT Token received)")

        # 3. Auth Me
        me_res = client.get("/auth/me", headers=headers)
        assert me_res.status_code == 200
        print(f"[OK] 3. Auth Current User: 200 OK ({me_res.json()['email']})")

        # 4. Profile
        prof_res = client.get("/profile/me", headers=headers)
        assert prof_res.status_code == 200, f"Profile failed: {prof_res.status_code} {prof_res.text}"
        profile_data = prof_res.json()
        print(f"[OK] 4. Profile: 200 OK (Target Roles: {profile_data.get('target_roles')})")

        # 5. Master Resume
        resume_res = client.get("/resumes/master", headers=headers)
        assert resume_res.status_code == 200, f"Resume failed: {resume_res.status_code} {resume_res.text}"
        resume_data = resume_res.json()
        skills = resume_data.get("parsed", {}).get("skills", [])
        print(f"[OK] 5. Master Resume: 200 OK ({len(skills)} parsed skills)")

        # 6. Dashboard Intelligence
        dash_res = client.get("/intelligence/dashboard", headers=headers)
        assert dash_res.status_code == 200, f"Dashboard failed: {dash_res.status_code}"
        dash_data = dash_res.json()
        print(f"[OK] 6. Dashboard Intelligence: 200 OK (RRI: {dash_data['role_readiness_index']}%, ATS: {dash_data['ats_compatibility']}%)")

        # 7. Recommended Job Matches
        jobs_res = client.get("/matches/recommended", headers=headers)
        assert jobs_res.status_code == 200, f"Matches failed: {jobs_res.status_code}"
        matches = jobs_res.json()
        assert len(matches) > 0
        first_job = matches[0]
        print(f"[OK] 7. Job Matches: 200 OK ({len(matches)} matches ranked, top match: {first_job['job_title']} at {first_job['company']} - {first_job['overall_score']}%)")

        # 8. Deterministic ATS Platform Evaluation
        ats_res = client.get(f"/intelligence/ats/{first_job['job_id']}?platform=workday", headers=headers)
        assert ats_res.status_code == 200, f"ATS failed: {ats_res.status_code}"
        ats_data = ats_res.json()
        p_name = ats_data.get('platform_compliance', {}).get('platform_name', 'Workday')
        guidance = ats_data.get('match_guidance', {}).get('label', 'Match Analysis')
        print(f"[OK] 8. ATS Platform Engine: 200 OK (Overall: {ats_data['overall']}%, Platform: {p_name}, Guidance: {guidance})")

        # 9. Skill Gaps Analysis
        gaps_res = client.get("/learning/gaps?role=Full%20Stack%20Developer", headers=headers)
        assert gaps_res.status_code == 200, f"Gaps failed: {gaps_res.status_code}"
        gaps = gaps_res.json()
        print(f"[OK] 9. Skill Gap Analysis: 200 OK ({len(gaps)} missing/partial skills identified)")

        # 10. Learning Roadmap
        roadmap_res = client.get("/learning/roadmap?role=Full%20Stack%20Developer", headers=headers)
        assert roadmap_res.status_code == 200, f"Roadmap failed: {roadmap_res.status_code}"
        roadmap = roadmap_res.json()
        print(f"[OK] 10. Learning Roadmap: 200 OK ({len(roadmap['immediate'])} immediate goals)")

        # 11. Interview Preparation
        interview_res = client.get("/interview/questions?role=Full%20Stack%20Developer", headers=headers)
        assert interview_res.status_code == 200, f"Interview failed: {interview_res.status_code}"
        questions = interview_res.json()["questions"]
        print(f"[OK] 11. Interview Preparation: 200 OK ({len(questions)} categorized STAR questions)")

        # 12. Achievement Journal
        ach_res = client.get("/resumes/achievements", headers=headers)
        assert ach_res.status_code == 200, f"Achievements failed: {ach_res.status_code}"
        achievements = ach_res.json()
        print(f"[OK] 12. Achievement Journal: 200 OK ({len(achievements)} verified wins)")

        # 13. Truth Guard Resume Tailoring Generation
        tailor_res = client.post("/tailoring/generate", json={"job_id": first_job["job_id"]}, headers=headers)
        assert tailor_res.status_code == 200
        tailor_data = tailor_res.json()
        version_id = tailor_data["id"]
        changes = tailor_data["changes"]
        print(f"[OK] 13. Truth Guard Tailoring: 200 OK (Generated v{version_id} with {len(changes)} evidence-backed changes)")

        # 14. Tailored Versions List
        versions_res = client.get("/tailoring", headers=headers)
        assert versions_res.status_code == 200
        print(f"[OK] 14. Tailored Versions List: 200 OK ({len(versions_res.json())} versions stored)")

        # 15. Export ATS PDF & DOCX
        pdf_res = client.get(f"/tailoring/{version_id}/export/pdf?template=modern", headers=headers)
        assert pdf_res.status_code == 200 and len(pdf_res.content) > 500
        print(f"[OK] 15. PDF Export Pipeline: 200 OK ({len(pdf_res.content)} bytes generated)")

        docx_res = client.get(f"/tailoring/{version_id}/export/docx?template=modern", headers=headers)
        assert docx_res.status_code == 200 and len(docx_res.content) > 500
        print(f"[OK] 16. DOCX Export Pipeline: 200 OK ({len(docx_res.content)} bytes generated)")

        # 17. Application CRM Tracker Save
        app_res = client.post(f"/applications/{first_job['job_id']}", headers=headers)
        assert app_res.status_code in [200, 201]
        print(f"[OK] 17. Application Tracker: 200 OK (Saved application for {first_job['company']})")

    print("=" * 60)
    print("[PASSED] ALL 17 SYSTEM ENDPOINTS PASSED WITH ZERO ERRORS!")
    print("=" * 60)

if __name__ == "__main__":
    run_smoke_test()
