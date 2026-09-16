import sys
import os
import time
import statistics

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.resume.models import (
    CandidateProfile,
    EducationEntity,
    ProjectEntity,
    WorkExperienceEntity,
)
from app.modules.tailoring.strategy import build_resume_strategy
from app.modules.tailoring.validation import (
    detect_fabricated_claims,
    detect_unsupported_metrics,
    detect_unsupported_action_verbs_and_scope,
    validate_final_tailored_resume,
)
from app.modules.intelligence.ats_score import compute_ats_score
from app.modules.tailoring.export import generate_pdf, generate_docx

# Realistic candidate resume
test_resume = {
    "personal": {
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "phone": "+1-555-0199",
        "location": "San Francisco, CA",
        "linkedin": "linkedin.com/in/janedoe",
        "github": "github.com/janedoe",
    },
    "summary": "Full Stack Software Engineer with 4 years experience designing and operating web applications.",
    "skills": ["Python", "React", "TypeScript", "PostgreSQL", "FastAPI", "Docker", "Redis", "TailwindCSS"],
    "experience_raw": [
        "TechCorp — San Francisco, CA\nSoftware Engineer (2022 - Present)\n• Developed REST APIs using FastAPI and PostgreSQL, serving 100k daily requests.\n• Optimized React frontend state management, reducing bundle size by 25%.\n• Containerized microservices using Docker and automated CI/CD deployment pipelines.",
        "StartupX — San Jose, CA\nJunior Software Developer (2020 - 2022)\n• Built reusable UI components with React and TypeScript for SaaS dashboard.\n• Automated database schema migrations and reduced query latencies by 30%."
    ],
    "projects_raw": [
        "Distributed Task Queue\nTechnologies: Python, Redis, Docker\n• Engineered an asynchronous task queue handling 5,000 tasks/second with Redis.\n• Implemented exponential backoff and dead-letter queue for resilient job execution."
    ],
    "education_raw": [
        "University of California, Berkeley\nB.S. in Computer Science (2016 - 2020)\nGPA: 3.8 / 4.0"
    ],
    "certifications": [
        "AWS Certified Solutions Architect - Associate"
    ],
    "achievements": [
        "1st Place, UC Berkeley Hackathon 2020"
    ]
}

jd_text = "Looking for a Software Engineer with Python, React, PostgreSQL, and Docker. Experience with microservices and CI/CD pipelines preferred."

def measure(fn, n=10):
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        times.append(t1 - t0)
    return statistics.mean(times) * 1000, max(times) * 1000

# 1. Strategy
profile = CandidateProfile.from_parsed_dict(test_resume, "")
strat_mean, strat_max = measure(lambda: build_resume_strategy(profile, target_role="Software Engineer"))

# 2. Truth Guard
def run_tg():
    detect_fabricated_claims("Built a web app.", "Developed responsive React web app.", jd_text, test_resume["skills"])
    detect_unsupported_metrics("Built a web app.", "Developed responsive React web app.")
    detect_unsupported_action_verbs_and_scope("Built a web app.", "Developed responsive React web app.")
    validate_final_tailored_resume(test_resume, test_resume)
tg_mean, tg_max = measure(run_tg)

# 3. ATS Analysis
def run_ats():
    compute_ats_score(
        resume_text="Jane Doe\nPython, React, PostgreSQL",
        jd_text=jd_text,
        parseability_score=90,
        recruiter_impact_score=80,
        skill_match_score=85,
        role_match_score=80,
    )
ats_mean, ats_max = measure(run_ats)

# 4. PDF Export (4 templates)
pdf_results = {}
for t in ["modern", "classic", "executive", "harvard"]:
    mean_ms, max_ms = measure(lambda: generate_pdf(test_resume, candidate_name="Jane Doe", template=t))
    pdf_results[t] = (mean_ms, max_ms)

# 5. DOCX Export (4 templates)
docx_results = {}
for t in ["modern", "classic", "executive", "harvard"]:
    mean_ms, max_ms = measure(lambda: generate_docx(test_resume, candidate_name="Jane Doe", template=t))
    docx_results[t] = (mean_ms, max_ms)

print("--- PERFORMANCE BENCHMARK RESULTS ---")
print(f"Resume Strategy: Mean={strat_mean:.2f}ms, Max={strat_max:.2f}ms")
print(f"Truth Guard Audit: Mean={tg_mean:.2f}ms, Max={tg_max:.2f}ms")
print(f"ATS Analysis: Mean={ats_mean:.2f}ms, Max={ats_max:.2f}ms")
print("PDF Export:")
for t, (mean_ms, max_ms) in pdf_results.items():
    print(f"  {t.capitalize()}: Mean={mean_ms:.2f}ms, Max={max_ms:.2f}ms")
print("DOCX Export:")
for t, (mean_ms, max_ms) in docx_results.items():
    print(f"  {t.capitalize()}: Mean={mean_ms:.2f}ms, Max={max_ms:.2f}ms")
