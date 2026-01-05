"""
FastAPI application entry point.
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import uuid

from app.core.config import settings
from app.core.logging import LoggerConfigurator
from app.core.limiter import limiter
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    create_error_response,
)
from app.api.endpoints import router as api_router
from app.api.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    LoggerConfigurator.setup()
    logger.info("🚀 Application startup")
    
    # Start background job worker
    from app.services.job_worker import get_job_worker
    worker = get_job_worker()
    await worker.start()
    logger.info("🔄 Background job worker started")
    
    yield
    
    # Stop background job worker
    await worker.stop()
    logger.info("🛑 Background job worker stopped")
    logger.info("🛑 Application shutdown")


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)


# MARK: - CORS MIDDLEWARE
# Note: Middleware executes in reverse order of addition.
# CORS must be the outermost layer to handle preflight OPTIONS requests
# before any exception handlers or other middleware interfere.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# MARK: - REQUEST CONTEXT MIDDLEWARE
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Add request ID to logging context and response headers."""
    request_id = str(uuid.uuid4())
    with logger.contextualize(request_id=request_id):
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# MARK: - RATE LIMITER
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# MARK: - EXCEPTION HANDLERS
app.add_exception_handler(AppException, app_exception_handler)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Convert HTTPException to RFC 7807 format."""
    return create_error_response(
        request=request,
        status_code=exc.status_code,
        error_type=f"https://problems.example.com/http-{exc.status_code}",
        title=exc.detail if isinstance(exc.detail, str) else "HTTP Error",
        detail=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with RFC 7807 format."""
    logger.exception(f"Unhandled exception: {exc}")
    return create_error_response(
        request=request,
        status_code=500,
        error_type="https://problems.example.com/internal-error",
        title="Internal Server Error",
        detail="An unexpected error occurred. Please try again later.",
    )


# MARK: - ROUTERS
app.include_router(auth_router)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "project": settings.PROJECT_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
