from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.mongo import connect_to_mongo, close_mongo_connection, ensure_indexes, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    await ensure_indexes()

    from app.modules.jobs.services import ensure_seed_loaded
    await ensure_seed_loaded(get_db())

    yield
    await close_mongo_connection()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get(f"{settings.API_PREFIX}/health")
    async def health():
        return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}

    # Module routers, registered as each phase implements them.
    from app.modules.auth.routes import router as auth_router
    from app.modules.profile.routes import router as profile_router
    from app.modules.chatbot.routes import router as chatbot_router
    from app.modules.resume.routes import router as resume_router
    from app.modules.jobs.routes import router as jobs_router
    from app.modules.matching.routes import router as matching_router
    from app.modules.tailoring.routes import router as tailoring_router
    from app.modules.intelligence.routes import router as intelligence_router
    from app.modules.applications.routes import router as applications_router
    from app.modules.learning.routes import router as learning_router
    from app.modules.interview.routes import router as interview_router

    app.include_router(auth_router, prefix=f"{settings.API_PREFIX}/auth", tags=["auth"])
    app.include_router(profile_router, prefix=f"{settings.API_PREFIX}/profile", tags=["profile"])
    app.include_router(chatbot_router, prefix=f"{settings.API_PREFIX}/copilot", tags=["copilot"])
    app.include_router(resume_router, prefix=f"{settings.API_PREFIX}/resumes", tags=["resumes"])
    app.include_router(jobs_router, prefix=f"{settings.API_PREFIX}/jobs", tags=["jobs"])
    app.include_router(matching_router, prefix=f"{settings.API_PREFIX}/matches", tags=["matching"])
    app.include_router(tailoring_router, prefix=f"{settings.API_PREFIX}/tailoring", tags=["tailoring"])
    app.include_router(intelligence_router, prefix=f"{settings.API_PREFIX}/intelligence", tags=["intelligence"])
    app.include_router(applications_router, prefix=f"{settings.API_PREFIX}/applications", tags=["applications"])
    app.include_router(learning_router, prefix=f"{settings.API_PREFIX}/learning", tags=["learning"])
    app.include_router(interview_router, prefix=f"{settings.API_PREFIX}/interview", tags=["interview"])

    # Phase 8 is UI polish only -- no new backend routers.

    return app


app = create_app()
