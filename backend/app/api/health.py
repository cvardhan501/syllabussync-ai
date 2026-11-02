import time
import asyncio
import logging
from typing import Optional, Tuple
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse
from app.models.database import get_db_connection

logger = logging.getLogger("syllabus_sync.health")

router = APIRouter(tags=["Health"])

_LAST_HEALTH_CHECK_TIME: float = 0.0
_CACHED_DB_STATUS: Tuple[bool, str] = (True, "connected")
_CACHED_DB_OK: Optional[bool] = True
_HEALTH_CACHE_TTL_SUCCESS = 15.0  # Cache successful DB probe for 15s to reduce connection churn
_HEALTH_CACHE_TTL_FAILURE = 3.0   # Short failure TTL (3s) so recovery is detected promptly
_HEALTH_LOCK = asyncio.Lock()



def _check_db_sync() -> Tuple[bool, str]:
    """
    Direct synchronous database ping with strict timeout.
    Returns (True, 'connected') if reachable, or (False, 'degraded') if timeout/failure.
    """
    try:
        from app.models.database import is_postgres, psycopg, _normalize_pg_url
        if is_postgres():
            if psycopg is None:
                return False, "degraded"
            pg_url = _normalize_pg_url(settings.database_url)
            connect_kwargs = {
                "connect_timeout": 1,
                "autocommit": True,
            }
            if "sslmode=" not in pg_url:
                connect_kwargs["sslmode"] = "require"
            with psycopg.connect(pg_url, **connect_kwargs) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True, "connected"
        else:
            with get_db_connection() as conn:
                conn.execute("SELECT 1")
                return True, "connected"
    except Exception as e:
        logger.warning(f"Database check skipped or failed during health verification: {e}")
        return False, "degraded"


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """
    Lightweight application health status endpoint.
    Used for uptime verification and frontend connectivity checks.
    
    Guarantees:
    - Backend availability is separated from database readiness.
    - FastAPI responds immediately: a database timeout never marks FastAPI as offline.
    - Concurrent requests do not stack worker threads or exhaust connection pools.
    - Database failure is never permanently cached (re-probes every 3s).
    """
    global _LAST_HEALTH_CHECK_TIME, _CACHED_DB_STATUS, _CACHED_DB_OK
    now = time.time()
    db_ok, db_status = _CACHED_DB_STATUS
    ttl = _HEALTH_CACHE_TTL_SUCCESS if db_ok else _HEALTH_CACHE_TTL_FAILURE

    if (now - _LAST_HEALTH_CHECK_TIME) >= ttl:
        # If another coroutine is already performing a DB probe, reuse current status to prevent pileup
        if not _HEALTH_LOCK.locked():
            try:
                async with _HEALTH_LOCK:
                    now = time.time()
                    ttl = _HEALTH_CACHE_TTL_SUCCESS if _CACHED_DB_STATUS[0] else _HEALTH_CACHE_TTL_FAILURE
                    if (now - _LAST_HEALTH_CHECK_TIME) >= ttl:
                        try:
                            db_ok, db_status = await asyncio.wait_for(
                                asyncio.to_thread(_check_db_sync),
                                timeout=1.2
                            )
                        except (asyncio.TimeoutError, Exception) as e:
                            logger.warning(f"Health DB check timed out or failed: {e}")
                            db_ok, db_status = False, "degraded"
                        _CACHED_DB_STATUS = (db_ok, db_status)
                        _CACHED_DB_OK = db_ok
                        _LAST_HEALTH_CHECK_TIME = time.time()
                    else:
                        db_ok, db_status = _CACHED_DB_STATUS
                        _CACHED_DB_OK = db_ok
            except Exception as e:
                logger.warning(f"Unexpected error in health probe lock: {e}")
                db_ok, db_status = False, "degraded"
                _CACHED_DB_OK = False


    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        database_connected=db_ok,
        database_status=db_status,
    )


