import logging
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse
from app.models.database import get_db_connection

logger = logging.getLogger("syllabus_sync.health")

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """
    Application health status endpoint.
    Used for uptime verification and frontend connectivity checks.
    Reports backend availability and safe database readiness status.
    """
    db_ok = None
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
            db_ok = True
    except Exception as e:
        logger.warning(f"Database check skipped or failed during health verification: {e}")
        db_ok = False

    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        database_connected=db_ok,
    )

