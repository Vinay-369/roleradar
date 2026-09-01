import json
import re
from app.modules.resume.parsing.structurer import (
    _clean_raw_text_artifacts,
    _split_into_sections,
    structure_resume_text,
    extract_candidate_profile,
    _bulletize,
)
from app.modules.resume.models import CandidateProfile
from app.modules.resume.parsing.action_verbs import strengthen_bullet_verb


AKHIL_RANA_RESUME = """AKHIL RANA
akhil.rana@example.com | +91 9876543210 | Bengaluru, India | linkedin.com/in/akhil-rana

PROFESSIONAL SUMMARY
Experienced Senior Software Engineer with 4+ years of expertise in system software, macOS/iOS client engineering, cloud infrastructure, and full-stack development.

TECHNICAL SKILLS
Languages: Python, Swift, Objective-C, Go, JavaScript, TypeScript, C++, Shell
Frameworks & Tools: FastAPI, React, Node.js, Docker, Kubernetes, AWS, CoreWLAN, Git, CI/CD, Terraform
Databases: PostgreSQL, Redis, MongoDB, MySQL

WORK EXPERIENCE
Juniper Networks
Software Engineer - 3 (April 2024 - Present)
Software Engineer - 2 (April 2022 - March 2024)
Software Engineer Intern (January 2022 - March 2022)
Bengaluru, India

Marvis Client - MacOS/iOS Development:
• Maintained and enhanced the Marvis Client daemon application for macOS and iOS, delivering enterprise telemetry collection using CoreWLAN and system APIs.
• Architected automated network onboarding workflows supporting 40k monthly active users across Fortune 500 enterprise deployments.
• Built Marvis-CLI diagnostic utility in Swift, reducing network troubleshooting time for IT administrators by 70%.

Application Infrastructure & Packaging:
• Architected modular application packaging pipelines, achieving a 99.8% installer success rate across diverse macOS environments.
• Optimized binary build sizes with a 65% package-size reduction through dynamic framework linkage and asset pruning.
• Automated CI/CD and release pipelines via GitHub Actions and Jenkins, reducing release cycle duration from 3 hours to 10 minutes (90% manual effort reduction).

Indoor Location SDK & Platform:
• Engineered real-time indoor location tracking SDK components handling high-frequency telemetry packets.
• Integrated Bluetooth Low Energy (BLE) and Wi-Fi signal processing algorithms, improving location accuracy by 35%.

Full-Stack Development & Microservices (Freelance / Advisory):
• Led development of a full-stack scheduling and payment platform using FastAPI, React, and PostgreSQL, processing $200k+ transactions.
• Optimized database indexing and query execution plans, delivering a 45% page-load improvement.
• Consolidated third-party API dependencies, achieving an 80% SaaS spend reduction for the client.

EDUCATION
Bachelor of Technology in Computer Science and Engineering (2018 - 2022)
National Institute of Technology — CGPA: 8.8 / 10.0
"""

def diagnose():
    print("==================================================")
    print("DIAGNOSING WORK EXPERIENCE STRUCTURAL PIPELINE")
    print("==================================================\n")

    # Stage 1: Raw text & normalized lines
    cleaned = _clean_raw_text_artifacts(AKHIL_RANA_RESUME)
    lines = cleaned.split("\n")
    print(f"Stage 1 & 2: Cleaned raw text into {len(lines)} lines.\n")

    # Stage 3: Section detection
    sections = _split_into_sections(lines)
    exp_lines = sections.get("experience", [])
    print(f"Stage 3: Section detection -> 'experience' section extracted with {len(exp_lines)} lines:")
    for idx, l in enumerate(exp_lines):
        print(f"  [{idx:02d}] {l}")
    print()

    # Stage 4: Current structure_resume_text output
    struct = structure_resume_text(cleaned)
    exp_raw = struct.get("experience_raw", [])
    print(f"Stage 4: structure_resume_text -> experience_raw produced {len(exp_raw)} items:")
    for idx, item in enumerate(exp_raw):
        print(f"  [{idx:02d}] {repr(item)}")
    print()

    # Stage 5: CandidateProfile extracted
    profile = extract_candidate_profile(cleaned)
    print(f"Stage 5: extract_candidate_profile -> {len(profile.experience)} WorkExperienceEntities:")
    for e_idx, exp in enumerate(profile.experience):
        print(f"  Entity {e_idx}: Company='{exp.company}', Role='{exp.role}', Dates='{exp.dates}', Location='{exp.location}'")
        print(f"    Bullets count: {len(exp.bullets)}")
        for b_idx, b in enumerate(exp.bullets):
            print(f"      Bullet {b_idx}: {repr(b)}")
    print()

    # Stage 6: Verb strengthening / Tailoring input check
    print("Stage 6: Verb-strengthening on current experience_raw:")
    for idx, b in enumerate(exp_raw):
        res, changed = strengthen_bullet_verb(b, default_verb="Developed")
        print(f"  [{idx:02d}] Original:  {repr(b)}")
        print(f"       Result:    {repr(res)} (changed={changed})\n")

if __name__ == "__main__":
    diagnose()
