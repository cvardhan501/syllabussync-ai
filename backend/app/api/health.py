import time
import asyncio
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
_HEALTH_CACHE_TTL = 30.0  # Cache DB connection status for 30s to reduce connection churn and eliminate thread pool blocking


def _check_db_sync() -> bool:
    try:
        from app.models.database import is_postgres, psycopg, _normalize_pg_url
        if is_postgres():
            if psycopg is None:
                return False
            pg_url = _normalize_pg_url(settings.database_url)
            connect_kwargs = {
                "connect_timeout": 2,
                "autocommit": True,
            }
            if "sslmode=" not in pg_url:
                connect_kwargs["sslmode"] = "require"
            with psycopg.connect(pg_url, **connect_kwargs) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        else:
            with get_db_connection() as conn:
                conn.execute("SELECT 1")
                return True
    except Exception as e:
        logger.warning(f"Database check skipped or failed during health verification: {e}")
        return False


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """
    Lightweight application health status endpoint.
    Used for uptime verification and frontend connectivity checks.
    Reports backend availability and safe database readiness status.
    Guaranteed fast response: does not wait for AI or external services,
    and DB probe is non-blocking with strict timeout and brief caching.
    """
    global _LAST_HEALTH_CHECK_TIME, _CACHED_DB_OK
    now = time.time()
    if _CACHED_DB_OK is not None and (now - _LAST_HEALTH_CHECK_TIME < _HEALTH_CACHE_TTL):
        db_ok = _CACHED_DB_OK
    else:
        try:
            db_ok = await asyncio.wait_for(asyncio.to_thread(_check_db_sync), timeout=2.0)
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"Health DB check timed out or failed: {e}")
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

