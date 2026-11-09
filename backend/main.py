import sys
from pathlib import Path

# Ensure repository root is in sys.path so 'import backend' works from any working directory
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from backend.config import settings
    from backend.database import engine, Base
    from backend.routers import (
        demo, sources, analysis, claims, timeline,
        questions, review, handover, activity, dashboard
    )
except ImportError:
    from config import settings
    from database import engine, Base
    from routers import (
        demo, sources, analysis, claims, timeline,
        questions, review, handover, activity, dashboard
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("handoverledger")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite / PostgreSQL tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not set. Live AI extraction will prompt for an API key. Precomputed demo cache is available.")
    yield

app = FastAPI(
    title="HandoverLedger API",
    description="Factual, verifiable project state reconstruction and handover ledger.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sanitize exceptions so secrets / tokens are NEVER leaked in error responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    err_msg = str(exc)
    # Mask any potential secret tokens from the error message string
    for secret in [settings.GEMINI_API_KEY, settings.GITHUB_TOKEN, settings.SUPABASE_SERVICE_ROLE_KEY]:
        if secret and secret in err_msg:
            err_msg = err_msg.replace(secret, "[REDACTED_SECRET]")

    logger.error(f"Unhandled server error on {request.url.path}: {err_msg}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Details have been safely logged."}
    )

# Include routers under /api prefix
api_prefix = "/api"
app.include_router(demo.router, prefix=api_prefix)
app.include_router(sources.router, prefix=api_prefix)
app.include_router(analysis.router, prefix=api_prefix)
app.include_router(claims.router, prefix=api_prefix)
app.include_router(timeline.router, prefix=api_prefix)
app.include_router(questions.router, prefix=api_prefix)
app.include_router(review.router, prefix=api_prefix)
app.include_router(handover.router, prefix=api_prefix)
app.include_router(activity.router, prefix=api_prefix)
app.include_router(dashboard.router, prefix=api_prefix)

if __name__ == "__main__":
    import uvicorn
    app_target = "main:app" if Path("main.py").exists() else "backend.main:app"
    uvicorn.run(app_target, host="0.0.0.0", port=8000, reload=True)

