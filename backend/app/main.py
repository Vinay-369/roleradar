from contextlib import asynccontextmanager
import asyncio
import logging
import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db.mongo import connect_to_mongo, close_mongo_connection, ensure_indexes, get_db

logger = logging.getLogger("roleradar.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.GENERATED_DIR).mkdir(parents=True, exist_ok=True)
    await connect_to_mongo()
    await ensure_indexes()

    from app.modules.jobs.services import ensure_seed_loaded
    await ensure_seed_loaded(get_db())

    from app.modules.auth.services import ensure_demo_user
    if settings.ENV.lower() != "production":
        await ensure_demo_user(get_db())

    from app.modules.jobs import services as jobs_services
    scheduler_task = None
    direct_refresh_enabled = (
        settings.JOB_REFRESH_INTERVAL_MINUTES > 0
        and jobs_services.has_configured_direct_ats_boards(settings)
    )
    aggregator_refresh_enabled = (
        settings.PUBLIC_AGGREGATOR_REFRESH_INTERVAL_MINUTES > 0
        and jobs_services.has_configured_public_aggregators(settings)
    )
    if settings.JOB_SOURCE_MODE == "direct_ats" and (direct_refresh_enabled or aggregator_refresh_enabled):
        scheduler_task = asyncio.create_task(
            jobs_services.scheduled_job_refresh_loop(get_db(), settings),
            name="scheduled-direct-ats-refresh",
        )

    try:
        yield
    finally:
        if scheduler_task:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass
        await close_mongo_connection()


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    app = FastAPI(
        title=settings.APP_NAME,
        lifespan=lifespan,
        docs_url="/docs" if settings.ENV.lower() != "production" else None,
        redoc_url="/redoc" if settings.ENV.lower() != "production" else None,
        openapi_url="/openapi.json" if settings.ENV.lower() != "production" else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count"],
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        supplied_request_id = request.headers.get("X-Request-ID", "")
        request_id = (
            supplied_request_id
            if supplied_request_id
            and len(supplied_request_id) <= 128
            and all(32 <= ord(char) <= 126 for char in supplied_request_id)
            else str(uuid4())
        )
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        if settings.ENV.lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid4()))
        logger.exception("Unhandled request error request_id=%s path=%s", request_id, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected server error occurred.", "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )

    async def database_status() -> str:
        try:
            db = get_db()
            await db.command("ping")
            return "connected"
        except Exception:
            return "disconnected"

    @app.get(f"{settings.API_PREFIX}/health/live")
    async def liveness():
        return {"status": "ok", "app": settings.APP_NAME}

    @app.get(f"{settings.API_PREFIX}/health/ready")
    async def readiness():
        from fastapi import HTTPException

        db_status = await database_status()
        if db_status != "connected":
            raise HTTPException(status_code=503, detail={"status": "not_ready", "database": db_status})
        return {"status": "ok", "app": settings.APP_NAME, "dependencies": {"database": db_status}}

    @app.get(f"{settings.API_PREFIX}/health")
    async def health():
        db_status = await database_status()

        is_healthy = (db_status == "connected")
        return {
            "status": "ok" if is_healthy else "degraded",
            "app": settings.APP_NAME,
            "env": settings.ENV,
            "dependencies": {
                "database": db_status
            }
        }

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

    # SPA Static Serving & Route Rewriting (Phase 10 Production Support)
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    # The source checkout keeps frontend/ beside backend/, while the release
    # image places both app/ and frontend/ directly under /app.
    dist_candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/dist")),
    ]
    dist_dir = next(
        (candidate for candidate in dist_candidates if os.path.isfile(os.path.join(candidate, "index.html"))),
        dist_candidates[0],
    )
    if os.path.exists(dist_dir) and os.path.isfile(os.path.join(dist_dir, "index.html")):
        assets_dir = os.path.join(dist_dir, "assets")
        if os.path.exists(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            clean_path = full_path.strip("/")
            # Never hijack /api routes or documentation
            if clean_path.startswith("api") or clean_path == "api" or clean_path in ("docs", "redoc", "openapi.json"):
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Endpoint not found")
            dist_root = Path(dist_dir).resolve()
            target = (dist_root / clean_path).resolve() if clean_path else dist_root
            if clean_path and dist_root in target.parents and target.is_file():
                return FileResponse(str(target))
            return FileResponse(os.path.join(dist_dir, "index.html"))

    return app


app = create_app()
