"""
MongoDB connection manager (Motor async driver).
One client for the app's lifetime; individual modules get collections
via get_collection(), never by importing the client directly.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    global _client, _db
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.MONGO_URI)
    _db = _client[settings.MONGO_DB_NAME]
    # Fail fast on startup if Mongo isn't reachable, rather than on first request.
    await _client.admin.command("ping")


async def close_mongo_connection() -> None:
    global _client
    if _client is not None:
        _client.close()


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not initialized. Did the app startup event run?")
    return _db


def get_collection(name: str):
    return get_db()[name]


# Canonical collection names, kept in one place to avoid typos scattered across modules.
class Collections:
    USERS = "users"
    PROFILES = "profiles"
    MASTER_RESUMES = "master_resumes"
    RESUME_VERSIONS = "resume_versions"
    RESUME_ANALYSES = "resume_analyses"
    JOBS = "jobs"
    JOB_MATCHES = "job_matches"
    APPLICATIONS = "applications"
    SKILL_GAPS = "skill_gaps"
    LEARNING_PATHS = "learning_paths"
    ACHIEVEMENTS = "achievements"
    INTERVIEW_SESSIONS = "interview_sessions"
    CHAT_CONVERSATIONS = "chat_conversations"
    AI_OPERATIONS = "ai_operations"
    AUDIT_LOGS = "audit_logs"


async def ensure_indexes(db: AsyncIOMotorDatabase | None = None) -> None:
    """Create indexes needed from day one. Called once at startup."""
    if db is None:
        db = get_db()
    await db[Collections.USERS].create_index("email", unique=True)
    await db[Collections.PROFILES].create_index("user_id", unique=True)
    await db[Collections.MASTER_RESUMES].create_index("user_id")
    await db[Collections.RESUME_VERSIONS].create_index([("user_id", 1), ("job_id", 1)])
    await db[Collections.JOBS].create_index([("skills", 1), ("job_type", 1), ("location", 1)])
    await db[Collections.JOBS].create_index([("verification_status", 1), ("url_type", 1)])
    await db[Collections.JOBS].create_index([("source", 1), ("source_job_id", 1)])
    await db[Collections.JOBS].create_index("posted_at")
    await db[Collections.JOBS].create_index("last_verified_at")
    await db[Collections.JOBS].create_index([("company", 1), ("title", 1)])
    await db[Collections.JOB_MATCHES].create_index([("user_id", 1), ("job_id", 1)], unique=True)
    await db[Collections.APPLICATIONS].create_index([("user_id", 1), ("job_id", 1)])
    await db[Collections.ACHIEVEMENTS].create_index("user_id")
    await db[Collections.INTERVIEW_SESSIONS].create_index("user_id")
    await db[Collections.CHAT_CONVERSATIONS].create_index("user_id")
    await db[Collections.SKILL_GAPS].create_index("user_id")
    await db[Collections.LEARNING_PATHS].create_index("user_id")
    await db[Collections.AUDIT_LOGS].create_index("user_id")
