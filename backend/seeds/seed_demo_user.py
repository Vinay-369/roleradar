"""
Seed a demo user account with completed onboarding for quick local testing and evaluation.

Usage:
    cd backend
    .venv/Scripts/python seeds/seed_demo_user.py
"""
import asyncio
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# pyrefly: ignore [missing-import]
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.mongo import Collections


async def seed_demo_user():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    email = "demo@example.com"
    password = "Password123!"
    full_name = "Demo Candidate"
    phone = "+91 9876543210"

    # Check if user already exists
    existing = await db[Collections.USERS].find_one({"email": email})
    now = datetime.now(timezone.utc)

    if existing:
        user_id = existing["_id"]
        await db[Collections.USERS].update_one(
            {"_id": user_id},
            {
                "$set": {
                    "password_hash": hash_password(password),
                    "full_name": full_name,
                    "phone": phone,
                    "onboarding_completed": True,
                    "updated_at": now,
                }
            },
        )
        print(f"[RoleRadar] Updated existing demo user: {email}")
    else:
        user_doc = {
            "email": email,
            "password_hash": hash_password(password),
            "full_name": full_name,
            "phone": phone,
            "onboarding_completed": True,
            "created_at": now,
            "updated_at": now,
        }
        res = await db[Collections.USERS].insert_one(user_doc)
        user_id = res.inserted_id
        print(f"[RoleRadar] Created new demo user: {email}")

    # Seed profile
    profile_doc = {
        "user_id": str(user_id),
        "category": "FRESHER",
        "experience_years": 0.0,
        "current_role": None,
        "current_company": None,
        "target_roles": ["Full Stack Developer", "Backend Developer", "Software Engineer"],
        "industries": ["Product", "FinTech", "SaaS"],
        "min_lpa": 6.0,
        "preferred_locations": ["Bangalore", "Hyderabad", "Remote"],
        "remote_preference": "any",
        "internship_interested": True,
        "career_brief": "Passionate developer eager to build scalable web applications and AI-driven platforms.",
        "consent_text": "I understand RoleRadar will analyze my resume and job data to generate recommendations.",
        "consent_timestamp": now,
        "auto_apply_settings": {
            "tier": "manual",
            "min_match_score": 90,
            "max_per_day": 5,
        },
        "created_at": now,
        "updated_at": now,
    }

    await db[Collections.PROFILES].update_one(
        {"user_id": str(user_id)},
        {"$set": profile_doc},
        upsert=True,
    )
    print(f"[RoleRadar] Demo user profile initialized successfully.")

    # Seed initial Achievement Journal entries
    achievements_count = await db[Collections.ACHIEVEMENTS].count_documents({"user_id": str(user_id)})
    if achievements_count == 0:
        sample_achievements = [
            {
                "user_id": str(user_id),
                "title": "Optimized Backend API Latency by 42% with Redis Caching",
                "description": "Architected an in-memory Redis caching layer and indexed high-frequency SQL queries, slashing p99 latency from 450ms to 260ms.",
                "metrics": "42% latency reduction, 260ms p99 response time across 15k RPM",
                "skills_tags": ["Redis", "PostgreSQL", "FastAPI", "Performance Optimization"],
                "created_at": now,
            },
            {
                "user_id": str(user_id),
                "title": "Built Automated CI/CD Pipeline with Docker & GitHub Actions",
                "description": "Configured multi-stage Docker builds and GitHub Actions workflow reducing deployment cycle from 30 minutes to under 4 minutes.",
                "metrics": "86% deployment speed improvement (4 mins vs 30 mins)",
                "skills_tags": ["Docker", "GitHub Actions", "CI/CD", "DevOps"],
                "created_at": now,
            },
        ]
        await db[Collections.ACHIEVEMENTS].insert_many(sample_achievements)
        print("[RoleRadar] Seeded starter Achievement Journal entries for Truth Guard tailoring.")

    # Seed or Update Master Resume for demo user
    resume_doc = {
        "user_id": str(user_id),
        "version": 1,
        "is_active": True,
        "file_name": "Demo_Candidate_Resume.pdf",
        "file_type": "application/pdf",
        "raw_text": (
            "DEMO CANDIDATE\n"
            "demo@example.com | +91 9876543210 | Bangalore, India\n\n"
            "SUMMARY\n"
            "Passionate Full Stack Developer with hands-on experience building scalable Python, FastAPI, and React applications.\n\n"
            "TECHNICAL SKILLS\n"
            "Languages & Frameworks: Python, JavaScript, TypeScript, FastAPI, React, Node.js, HTML5, CSS3, Tailwind CSS\n"
            "Databases & Tools: PostgreSQL, MongoDB, Redis, Docker, Git, GitHub Actions, REST APIs, CI/CD\n\n"
            "EXPERIENCE & PROJECTS\n"
            "Full Stack Web Developer — RoleRadar AI\n"
            "- Built full-stack AI career copilot platform using FastAPI, React, and MongoDB.\n"
            "- Designed deterministic ATS scoring and parsing engine supporting Workday, Taleo, and Greenhouse formats.\n"
            "- Implemented Truth Guard evidence-based resume tailoring and Redis query caching for 42% faster response times.\n\n"
            "EDUCATION\n"
            "Bachelor of Technology in Computer Science & Engineering (2022 - 2026)\n"
        ),
        "parsed": {
            "personal": {
                "name": full_name,
                "email": email,
                "phone": phone,
                "location": "Bangalore, India",
            },
            "skills": [
                "Python", "FastAPI", "React", "TypeScript", "JavaScript",
                "Node.js", "PostgreSQL", "MongoDB", "Redis", "Docker",
                "Git", "GitHub Actions", "REST APIs", "CI/CD", "Tailwind CSS", "HTML5", "CSS3"
            ],
            "experience_raw": [
                "Built full-stack AI career copilot platform using FastAPI, React, and MongoDB.",
                "Designed deterministic ATS scoring and parsing engine supporting Workday, Taleo, and Greenhouse formats.",
                "Implemented Truth Guard evidence-based resume tailoring and Redis query caching for 42% faster response times."
            ],
            "projects_raw": [
                "RoleRadar AI Career Intelligence Copilot with deterministic match scoring.",
                "High-throughput Redis cache pipeline slashing p99 latency to 260ms."
            ],
            "education_raw": [
                "Bachelor of Technology in Computer Science & Engineering (2022 - 2026)"
            ]
        },
        "parseability": {
            "score": 92,
            "issues": [],
            "detected_sections": ["summary", "skills", "experience", "projects", "education"],
            "missing_standard_sections": [],
            "contact_info_found": {"email": True, "phone": True, "location": True},
            "likely_multi_column": False,
            "word_count": 340,
        },
        "recruiter_impact": {
            "score": 88,
            "bullets_analyzed": 5,
            "quantified_bullets": 4,
            "weak_verb_bullets": 0,
            "quantification_rate": 0.80,
            "issues": ["Good STAR metrics formatting and action verb usage."],
        },
        "action_verbs": {
            "score": 95,
            "total_bullets": 5,
            "strong_verb_bullets": 5,
            "weak_verb_bullets": 0,
            "power_verb_rate": 1.0,
            "strong_verbs_found": ["architected", "optimized", "engineered", "spearheaded", "designed"],
            "weak_verbs_found": [],
            "issues": [],
            "recommendations": [],
        },
        "skills_depth": {
            "score": 90,
            "total_skills": 16,
            "verified_skills_count": 16,
            "domain_coverage_count": 5,
            "categorized_domains": [
                {"id": "languages", "name": "Programming Languages", "items": ["Python", "TypeScript", "JavaScript", "SQL", "C++"]},
                {"id": "frameworks", "name": "Frameworks & Web Technologies", "items": ["FastAPI", "React", "Node.js", "Next.js", "Express", "TailwindCSS"]},
                {"id": "databases", "name": "Databases & Storage Systems", "items": ["PostgreSQL", "Redis", "MongoDB"]},
                {"id": "devops_cloud", "name": "Cloud, Containers & DevOps", "items": ["Docker", "AWS", "Git", "CI/CD", "Linux"]},
                {"id": "core_cs_tools", "name": "Core CS, Architecture & Tools", "items": ["Data Structures", "System Design"]},
            ],
            "missing_domains": [],
            "issues": [],
            "recommendations": [],
        },
        "strict_ats_score": 92,
        "ats_status": {
            "status": "passed",
            "label": "PASSED ATS FILTER — Shortlist Ready",
            "color": "text-signal-700 bg-signal-500/10 border-signal-500/30",
        },
        "created_at": now,
    }

    await db[Collections.MASTER_RESUMES].update_one(
        {"user_id": str(user_id), "is_active": True},
        {"$set": resume_doc},
        upsert=True,
    )
    print("[RoleRadar] Active Master Resume configured for demo user.")

    print("-" * 50)
    print("Demo Credentials:")
    print(f"  Email:    {email}")
    print(f"  Password: {password}")
    print("-" * 50)


if __name__ == "__main__":
    asyncio.run(seed_demo_user())
