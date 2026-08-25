"""
Auth business logic. Pure Python + repository calls — no framework
(FastAPI) concerns here, so it's directly unit-testable.
"""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth import repositories as repo


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


async def register_user(
    db: AsyncIOMotorDatabase,
    settings: Settings,
    email: str,
    password: str,
    full_name: str,
    phone: str | None,
) -> tuple[dict, str]:
    existing = await repo.get_user_by_email(db, email)
    if existing:
        raise EmailAlreadyRegisteredError(f"Email {email} is already registered.")

    password_hash = hash_password(password)
    user = await repo.create_user(db, email, password_hash, full_name, phone)
    token = create_access_token(subject=str(user["_id"]), settings=settings)
    return user, token


async def authenticate_user(
    db: AsyncIOMotorDatabase,
    settings: Settings,
    email: str,
    password: str,
) -> tuple[dict, str]:
    user = await repo.get_user_by_email(db, email)
    if not user or not verify_password(password, user["password_hash"]):
        raise InvalidCredentialsError("Invalid email or password.")

    token = create_access_token(subject=str(user["_id"]), settings=settings)
    return user, token


async def ensure_demo_user(db: AsyncIOMotorDatabase) -> dict:
    """
    Guarantees that demo@example.com exists with a valid password hash,
    profile, and master resume so testing and quick sign-in always succeed.
    """
    demo_email = "demo@example.com"
    demo_pass = "Password123!"

    user = await repo.get_user_by_email(db, demo_email)
    if user is None:
        pw_hash = hash_password(demo_pass)
        user = await repo.create_user(
            db,
            email=demo_email,
            password_hash=pw_hash,
            full_name="Demo Candidate",
            phone="+91 98765 43210",
        )
        # Mark onboarding completed
        from app.db.mongo import Collections
        await db[Collections.USERS].update_one(
            {"_id": user["_id"]},
            {"$set": {"onboarding_completed": True}}
        )

    user_id = str(user["_id"])

    # Ensure profile exists
    from app.modules.profile import repositories as profile_repo
    existing_profile = await profile_repo.get_profile(db, user_id)
    if existing_profile is None:
        await profile_repo.upsert_profile(
            db,
            user_id,
            {
                "full_name": "Demo Candidate",
                "target_roles": ["Full Stack Developer", "Backend Developer"],
                "workplace_preference": "remote",
                "preferred_locations": ["Bangalore", "Hyderabad", "Remote"],
                "min_lpa": 8,
                "linkedin_url": "https://linkedin.com/in/democandidate",
                "github_url": "https://github.com/democandidate",
                "portfolio_url": "https://democandidate.dev",
            },
        )

    # Ensure master resume exists
    from app.modules.resume import repositories as resume_repo
    active_resume = await resume_repo.get_active_master_resume(db, user_id)
    if active_resume is None:
        parsed_data = {
            "name": "Demo Candidate",
            "email": demo_email,
            "phone": "+91 98765 43210",
            "links": ["https://linkedin.com/in/democandidate", "https://github.com/democandidate"],
            "skills": [
                "Python", "TypeScript", "React", "Node.js", "FastAPI", "PostgreSQL",
                "Redis", "Docker", "Git", "REST APIs", "TailwindCSS", "Next.js",
                "MongoDB", "CI/CD", "System Design", "AWS"
            ],
            "experience_raw": [
                "Software Engineer at Acme Cloud Corp (2024 – Present): Architected RESTful microservices using Python and FastAPI, handling 15k+ daily requests and reducing API response latency by 32%.",
                "Full Stack Developer Intern at TechVentures (2023 – 2024): Built responsive dashboard interfaces in React and TypeScript with Redis caching, boosting page load speeds by 40%."
            ],
            "projects_raw": [
                "High-Throughput Distributed Task Engine: Designed an asynchronous task queue with Celery, Redis, and Docker processing 10k daily events with 99.9% uptime.",
                "E-Commerce Microservices Platform: Developed order management and inventory reservation services using FastAPI and PostgreSQL with Redlock distributed locking."
            ],
            "education_raw": [
                "B.Tech in Computer Science & Engineering (2020 – 2024) — CGPA: 8.8 / 10.0"
            ],
            "awards": ["1st Place — National Cloud Hackathon 2023"],
            "summary": "Full Stack Engineer with strong foundations in scalable distributed systems, RESTful API architecture, and modern TypeScript frontend development."
        }

        parseability = {
            "score": 92,
            "has_standard_headings": True,
            "single_column": True,
            "no_complex_tables": True,
            "contact_found": True,
            "issues": []
        }

        recruiter_impact = {
            "score": 88,
            "action_verb_count": 8,
            "quantified_metrics_count": 6,
            "strong_verbs_ratio": 0.85,
            "issues": []
        }

        raw_text = (
            "Demo Candidate\n"
            "demo@example.com | +91 98765 43210 | Bangalore, India | linkedin.com/in/democandidate | github.com/democandidate\n\n"
            "TECHNICAL SKILLS\n"
            "Languages: Python, TypeScript, JavaScript, SQL, C++\n"
            "Frameworks: FastAPI, React, Node.js, Next.js, Express, TailwindCSS\n"
            "Databases: PostgreSQL, Redis, MongoDB\n"
            "Cloud & DevOps: Docker, AWS, Git, CI/CD, Linux\n\n"
            "EXPERIENCE\n"
            "Software Engineer | Acme Cloud Corp | Jan 2024 – Present\n"
            "• Architected RESTful microservices using Python and FastAPI, handling 15k+ daily requests and reducing API latency by 32%.\n"
            "• Optimized PostgreSQL database queries with composite indexes, eliminating N+1 query bottlenecks.\n\n"
            "PROJECTS\n"
            "Distributed Task Engine | Python, Redis, Docker, Celery\n"
            "• Designed asynchronous background task processing pipeline handling 10k+ daily events with 99.9% uptime.\n\n"
            "EDUCATION\n"
            "B.Tech in Computer Science & Engineering | 2020 – 2024 | CGPA: 8.8"
        )

        await resume_repo.create_master_resume(
            db=db,
            user_id=user_id,
            version=1,
            file_name="demo_resume.pdf",
            file_type="application/pdf",
            raw_text=raw_text,
            parsed=parsed_data,
            parseability=parseability,
            recruiter_impact=recruiter_impact,
        )

    return user
