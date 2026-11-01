import time
import logging
from typing import Optional
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse
from app.models.database import get_db_connection

logger = logging.getLogger("syllabus_sync.health")

router = APIRouter(tags=["Health"])

_LAST_HEALTH_CHECK_TIME: float = 0.0
_CACHED_DB_OK: Optional[bool] = None
_HEALTH_CACHE_TTL = 15.0  # Cache DB connection status for 15s to reduce connection churn


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """
    Application health status endpoint.
    Used for uptime verification and frontend connectivity checks.
    Reports backend availability and safe database readiness status.
    Caches database connectivity verification briefly to eliminate connection storm overhead.
    """
    global _LAST_HEALTH_CHECK_TIME, _CACHED_DB_OK
    now = time.time()
    if _CACHED_DB_OK is not None and (now - _LAST_HEALTH_CHECK_TIME < _HEALTH_CACHE_TTL):
        db_ok = _CACHED_DB_OK
    else:
        try:
            with get_db_connection() as conn:
                conn.execute("SELECT 1")
                db_ok = True
        except Exception as e:
            logger.warning(f"Database check skipped or failed during health verification: {e}")
            db_ok = False
        _CACHED_DB_OK = db_ok
        _LAST_HEALTH_CHECK_TIME = now

    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        database_connected=db_ok,
    )

