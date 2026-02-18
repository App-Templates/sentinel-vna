import os
import signal
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from backend.api.admin_routes import router as admin_router
from backend.api.auth import require_auth, router as auth_router, setup_oauth
from backend.api.publisher_routes import router as publisher_router
from backend.api.rate_limit import limiter
from backend.api.routes import router
from backend.db.database import close_db, init_db
from backend.scheduler.scheduler import start_scheduler, stop_scheduler
from backend.utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PROD = ENVIRONMENT == "production"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Fail-fast: require a real SESSION_SECRET in production
if IS_PROD and os.getenv("SESSION_SECRET") in (None, "", "dev-secret-change-me"):
    raise RuntimeError(
        "SESSION_SECRET must be set to a secure value in production. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    )


def _handle_sigterm(signum, frame):
    """Handle SIGTERM by stopping scheduler gracefully before exit."""
    logger.info("Received SIGTERM, initiating graceful shutdown")
    stop_scheduler()
    close_db()
    raise SystemExit(0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Value Network Alerting System")
    init_db()
    start_scheduler()
    setup_oauth()
    signal.signal(signal.SIGTERM, _handle_sigterm)
    logger.info("Environment: %s", ENVIRONMENT)
    logger.info("Startup complete")
    yield
    logger.info("Shutting down")
    stop_scheduler()
    close_db()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Value Network Alerting System",
    description="Revenue anomaly detection and alerting for ad-tech value networks",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter


def _custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    retry_after = exc.detail.split()[-1] if exc.detail else "60"
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded", "retry_after": retry_after},
        headers={"Retry-After": retry_after},
    )


app.add_exception_handler(RateLimitExceeded, _custom_rate_limit_handler)

# Session middleware (required by authlib for OAuth state)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-secret-change-me"),
)

# CORS — restricted in production, open in development
if IS_PROD:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[FRONTEND_URL],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Auth routes (no auth required on these)
app.include_router(auth_router)

# API routes (auth required in production, bypassed in development)
app.include_router(router, dependencies=[Depends(require_auth)])
app.include_router(admin_router, dependencies=[Depends(require_auth)])
app.include_router(publisher_router, dependencies=[Depends(require_auth)])

# In production, serve the built frontend from frontend/dist/
if IS_PROD:
    _dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"

    if (_dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="static-assets")
    else:
        logger.warning("frontend/dist/assets not found — run 'npm run build' first")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve SPA index.html for non-API/auth routes."""
        if full_path.startswith(("api/", "auth/")):
            raise HTTPException(status_code=404, detail="Not found")
        index = _dist / "index.html"
        if not index.is_file():
            raise HTTPException(status_code=503, detail="Frontend not built")
        return FileResponse(str(index))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=not IS_PROD,
        # Single worker to prevent duplicate scheduler execution from lifespan
        workers=1,
    )
