import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api import api_router
from app.models.database import init_db
from app.services.youtube_client import (
    YouTubeApiException,
    YouTubeAuthException,
    YouTubeQuotaExceededException,
    YouTubeConnectionException,
)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("syllabus_sync")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database schema safely
    logger.info("Initializing SyllabusSync AI database...")
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization warning (non-fatal for serverless cold start): {e}")
    yield
    # Shutdown
    logger.info("Shutting down SyllabusSync AI backend.")
    try:
        from app.services.youtube_client import YouTubeClientService
        await YouTubeClientService.close_http_client()
    except Exception:
        pass


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="SyllabusSync AI backend API: Syllabus parsing, video matching, and adaptive study roadmap.",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Specific handler for YouTube API exceptions to return actionable status codes and messages
@app.exception_handler(YouTubeApiException)
async def youtube_exception_handler(request: Request, exc: YouTubeApiException):
    logger.warning(
        f"YouTube API exception during {request.method} {request.url.path}: {type(exc).__name__}: {str(exc)}"
    )
    if isinstance(exc, YouTubeQuotaExceededException):
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
        prefix = "YouTube Quota Exceeded"
    elif isinstance(exc, YouTubeAuthException):
        status_code = status.HTTP_502_BAD_GATEWAY
        prefix = "YouTube Authentication Error"
    elif isinstance(exc, YouTubeConnectionException):
        status_code = status.HTTP_504_GATEWAY_TIMEOUT
        prefix = "YouTube Connection Timeout"
    else:
        status_code = status.HTTP_502_BAD_GATEWAY
        prefix = "YouTube API Error"

    return JSONResponse(
        status_code=status_code,
        content={"detail": f"{prefix}: {str(exc)}"}
    )


# Global unhandled exception handler to protect filesystem paths & sensitive details
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error during {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred while processing your request. Please try again."
        }
    )


# Include API routes under /api
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs_url": "/docs",
        "health_check": "/api/health"
    }

