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
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

try:
    from backend.config import settings
    from backend.database import engine, Base
    from backend.sanitizer import (
        sanitize_text,
        sanitize_obj,
        install_logging_sanitizer,
    )
    from backend.gemini_client import GeminiServiceError
    from backend.routers import (
        demo, sources, analysis, claims, timeline,
        questions, review, handover, activity, dashboard, ask
    )
except ImportError:
    from config import settings
    from database import engine, Base
    from sanitizer import (
        sanitize_text,
        sanitize_obj,
        install_logging_sanitizer,
    )
    from gemini_client import GeminiServiceError
    from routers import (
        demo, sources, analysis, claims, timeline,
        questions, review, handover, activity, dashboard, ask
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
install_logging_sanitizer()
logger = logging.getLogger("handoverledger")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Database check and initialization
    db_type = "postgresql" if "postgres" in settings.DATABASE_URL.lower() else "sqlite"
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database: Connected and initialized successfully ({db_type}).")
    
    # 2. Startup AI check and logging
    try:
        from backend.gemini_client import gemini_client
        ai_res = gemini_client.check_health()
        if ai_res.get("ok"):
            logger.info(f"AI: Health check passed with model '{ai_res.get('model_in_use')}' (fallback_used={ai_res.get('fallback_used')}).")
        else:
            logger.warning(f"AI: Health check failed with error type '{ai_res.get('error_type')}'.")
    except Exception as e:
        logger.warning(f"AI: Health check failed with error: {e}")

    # 3. Startup GitHub check and logging
    try:
        from backend.ingestion.github import check_github_health
        gh_res = await check_github_health()
        if gh_res.get("reachable"):
            token_status = "token configured" if gh_res.get("token_configured") else "no token configured"
            rem = gh_res.get("remaining_rate_limit")
            rem_str = f", remaining={rem}" if rem is not None else ""
            logger.info(f"GitHub: API reachable ({token_status}{rem_str}).")
        else:
            logger.warning("GitHub: API check unreachable.")
    except Exception as e:
        logger.warning(f"GitHub: Health check failed with error: {e}")
        
    yield

app = FastAPI(
    title="HandoverLedger API",
    description="Factual, verifiable project state reconstruction and handover ledger.",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware to guarantee CORS headers on every response (including error responses and OPTIONS preflight)
@app.middleware("http")
async def cors_and_error_boundary_middleware(request: Request, call_next):
    origin = request.headers.get("origin")
    allowed_origins = settings.cors_origins_list

    # Handle preflight OPTIONS requests directly
    if request.method == "OPTIONS":
        response = JSONResponse(content={"ok": True}, status_code=200)
        if origin and (origin in allowed_origins or "*" in allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Demo-Role, X-Workspace-Id, Authorization, Accept, Origin, User-Agent, X-Requested-With"
            response.headers["Access-Control-Max-Age"] = "86400"
        return response

    try:
        response = await call_next(request)
    except Exception as exc:
        err_msg = sanitize_text(str(exc))
        logger.error(f"Unhandled server exception on {request.url.path}: {err_msg}")
        response = JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred. Details have been safely logged.",
                "detail": "An internal server error occurred. Details have been safely logged."
            }
        )

    # Attach CORS headers if request origin is authorized
    if origin and (origin in allowed_origins or "*" in allowed_origins):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Demo-Role, X-Workspace-Id, Authorization, Accept, Origin, User-Agent, X-Requested-With"
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition, Content-Type, X-Demo-Role, X-Workspace-Id"

    ws_id = request.headers.get("x-workspace-id")
    if ws_id:
        response.headers["X-Workspace-Id"] = ws_id

    return response

# CORS configuration outermost
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    allow_headers=["Content-Type", "X-Demo-Role", "X-Workspace-Id", "Authorization", "Accept", "Origin", "User-Agent", "X-Requested-With", "*"],
    expose_headers=["Content-Disposition", "Content-Type", "X-Demo-Role", "X-Workspace-Id"],
)

# Sanitize exceptions so secrets / tokens are NEVER leaked in error responses
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, str):
        sanitized_detail = sanitize_text(detail)
    elif isinstance(detail, (dict, list)):
        sanitized_detail = sanitize_obj(detail)
    else:
        sanitized_detail = sanitize_text(str(detail))
    
    error_code = "HTTP_ERROR"
    if exc.status_code == 404:
        error_code = "NOT_FOUND"
    elif exc.status_code == 400:
        error_code = "BAD_REQUEST"
    elif exc.status_code == 403:
        error_code = "FORBIDDEN"
    elif exc.status_code == 429:
        error_code = "RATE_LIMITED"
    elif exc.status_code >= 500:
        error_code = "INTERNAL_SERVER_ERROR"

    msg = sanitized_detail if isinstance(sanitized_detail, str) else str(sanitized_detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": error_code,
            "message": msg,
            "detail": sanitized_detail
        },
        headers=exc.headers
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    sanitized_errors = sanitize_obj(exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Invalid request payload format or parameters.",
            "detail": sanitized_errors
        }
    )

@app.exception_handler(GeminiServiceError)
async def gemini_service_error_handler(request: Request, exc: GeminiServiceError):
    return JSONResponse(
        status_code=502,
        content={
            "error_code": f"AI_{exc.error_type.upper()}",
            "message": sanitize_text(exc.friendly_message),
            "detail": sanitize_text(exc.friendly_message),
            "error_type": exc.error_type,
            "technical_detail": sanitize_text(exc.sanitized_details)
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    err_msg = sanitize_text(str(exc))
    logger.error(f"Unhandled server error on {request.url.path}: {err_msg}")
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred. Details have been safely logged.",
            "detail": "An internal server error occurred. Details have been safely logged."
        }
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
app.include_router(ask.router, prefix=api_prefix)

if __name__ == "__main__":
    import uvicorn
    app_target = "main:app" if Path("main.py").exists() else "backend.main:app"
    uvicorn.run(app_target, host="0.0.0.0", port=8000, reload=True)

