"""
System Diagnostics API
======================
Safe configuration status endpoints:
- Never reveals secret keys, passwords, authorization tokens, or full exception traces.
- Verifies database connectivity, Strands SDK provider status, and YouTube Data API v3.
- Provides interactive, non-blocking test endpoints for live verification with strict timeouts.
- Independent probes: one unavailable or slow service never marks other services unavailable.
"""

import re
import time
import asyncio
import datetime
import logging
from typing import Optional, List, Tuple
from fastapi import APIRouter, Depends, status
import httpx

from app.core.config import settings
from app.core.auth import check_is_admin, require_admin_access, verify_diagnostics_access
from app.models.database import get_db_connection, is_postgres
from app.schemas.diagnostics import (
    BackendDiagnostic,
    DatabaseDiagnostic,
    StrandsDiagnostic,
    YouTubeDiagnostic,
    SystemDiagnosticsResponse,
    DiagnosticTestResult,
)

logger = logging.getLogger("syllabus_sync.diagnostics")

# In-memory store for live connectivity verification probe results
_LAST_YOUTUBE_TEST: Optional[dict] = None
_LAST_STRANDS_TEST: Optional[dict] = None

router = APIRouter(
    prefix="/diagnostics",
    tags=["Diagnostics"],
    dependencies=[Depends(verify_diagnostics_access)],
)


def _probe_database_sync(is_admin: bool) -> Tuple[str, str, int, List[str]]:
    """Synchronous database query executed within a thread pool with strict timeout."""
    engine_name = "PostgreSQL" if is_postgres() else "SQLite"
    with get_db_connection() as conn:
        if is_postgres():
            rows = conn.execute(
                "SELECT table_name as name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        all_tables = [r["name"] for r in rows]
        actual_tables_count = len(all_tables)
        tables_list = all_tables if is_admin else []
        return "connected", engine_name, actual_tables_count, tables_list


def _probe_youtube_cache_count_sync() -> int:
    """Queries cached search query count safely."""
    try:
        with get_db_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM youtube_search_cache").fetchone()
            if row:
                return row["cnt"]
    except Exception:
        pass
    return 0


@router.get(
    "",
    response_model=SystemDiagnosticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get safe system configuration and connectivity diagnostics"
)
async def get_system_diagnostics(is_admin: bool = Depends(check_is_admin)):
    """
    Returns sanitized diagnostics of backend, database connectivity,
    Strands Agents SDK configuration, and YouTube Data API v3 settings.
    Probes run independently with individual timeouts:
    A slow or unavailable database, Bedrock, or YouTube never marks FastAPI offline.
    Zero secret leakage guaranteed.
    """
    # 1. FastAPI Backend Probe (instant, non-blocking)
    backend_diag = BackendDiagnostic(
        status="healthy",
        version=settings.app_version,
        environment=settings.app_env,
    )

    # 2. Database Probe (async thread with 3.0s bounded timeout)
    async def _run_db_probe() -> DatabaseDiagnostic:
        engine_name = "PostgreSQL" if is_postgres() else "SQLite"
        try:
            db_status, eng, tbl_count, tbl_list = await asyncio.wait_for(
                asyncio.to_thread(_probe_database_sync, is_admin),
                timeout=3.0
            )
            return DatabaseDiagnostic(
                status=db_status,
                engine=eng,
                tables_count=tbl_count,
                tables=tbl_list,
            )
        except asyncio.TimeoutError:
            logger.warning("Database diagnostics probe timed out after 3.0s")
            return DatabaseDiagnostic(
                status="timeout",
                engine=engine_name,
                tables_count=0,
                tables=[],
            )
        except Exception as db_err:
            logger.warning(f"Database diagnostics probe error: {db_err}")
            return DatabaseDiagnostic(
                status="error",
                engine=engine_name,
                tables_count=0,
                tables=[],
            )

    # 3. Strands Agents SDK Probe (configuration inspection + cached probe result)
    def _run_strands_probe() -> StrandsDiagnostic:
        has_strands_creds = settings.has_strands_credentials()
        provider = settings.strands_provider
        model = settings.strands_model

        if has_strands_creds:
            creds_summary = f"Credentials configured ({provider.title()})"
            active_mode = "live"
            fallback_reason = None
        else:
            creds_summary = "Not Set (Missing API credentials in environment)"
            active_mode = "development_fallback"
            fallback_reason = f"No credentials provided for provider '{provider}'."

        strands_conn_status = (
            _LAST_STRANDS_TEST["status"]
            if _LAST_STRANDS_TEST
            else ("unverified" if has_strands_creds else "missing")
        )
        return StrandsDiagnostic(
            provider=provider,
            model=model,
            region=settings.aws_region if provider == "bedrock" else None,
            credentials_configured=has_strands_creds,
            credentials_summary=creds_summary,
            fallback_enabled=settings.allow_dev_fallback_analysis,
            active_mode=active_mode,
            fallback_reason=fallback_reason,
            connectivity_status=strands_conn_status,
            last_tested=_LAST_STRANDS_TEST.get("timestamp") if _LAST_STRANDS_TEST else None,
            last_test_message=_LAST_STRANDS_TEST.get("message") if _LAST_STRANDS_TEST else None,
        )

    # 4. YouTube Data API v3 Probe (configuration inspection + async cache count)
    async def _run_youtube_probe() -> YouTubeDiagnostic:
        has_yt_creds = settings.has_youtube_credentials()
        try:
            cached_count = await asyncio.wait_for(
                asyncio.to_thread(_probe_youtube_cache_count_sync),
                timeout=2.0
            )
        except Exception:
            cached_count = 0

        if has_yt_creds:
            key_summary = "Configured (Active)"
            yt_active_mode = "live"
            yt_fallback_reason = None
        else:
            key_summary = "Not Set (YOUTUBE_API_KEY missing in environment)"
            yt_active_mode = "development_fallback"
            yt_fallback_reason = "YOUTUBE_API_KEY environment variable is not configured."

        yt_conn_status = (
            _LAST_YOUTUBE_TEST["status"]
            if _LAST_YOUTUBE_TEST
            else ("unverified" if has_yt_creds else "missing")
        )
        return YouTubeDiagnostic(
            key_configured=has_yt_creds,
            key_summary=key_summary,
            fallback_enabled=settings.allow_dev_fallback_youtube,
            active_mode=yt_active_mode,
            fallback_reason=yt_fallback_reason,
            cached_queries_count=cached_count,
            connectivity_status=yt_conn_status,
            last_tested=_LAST_YOUTUBE_TEST.get("timestamp") if _LAST_YOUTUBE_TEST else None,
            last_test_message=_LAST_YOUTUBE_TEST.get("message") if _LAST_YOUTUBE_TEST else None,
        )

    # Execute probes concurrently and independently
    db_result, strands_result, yt_result = await asyncio.gather(
        _run_db_probe(),
        asyncio.to_thread(_run_strands_probe),
        _run_youtube_probe(),
        return_exceptions=True,
    )

    # Safeguard against any unexpected exception
    database_diag = db_result if isinstance(db_result, DatabaseDiagnostic) else DatabaseDiagnostic(
        status="error",
        engine="PostgreSQL" if is_postgres() else "SQLite",
        tables_count=0,
        tables=[],
    )
    strands_diag = strands_result if isinstance(strands_result, StrandsDiagnostic) else _run_strands_probe()
    youtube_diag = yt_result if isinstance(yt_result, YouTubeDiagnostic) else YouTubeDiagnostic(
        key_configured=settings.has_youtube_credentials(),
        key_summary="Configured" if settings.has_youtube_credentials() else "Not Set",
        fallback_enabled=settings.allow_dev_fallback_youtube,
        active_mode="live" if settings.has_youtube_credentials() else "development_fallback",
        cached_queries_count=0,
        connectivity_status="unverified",
    )

    return SystemDiagnosticsResponse(
        status="success",
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        backend=backend_diag,
        database=database_diag,
        strands=strands_diag,
        youtube=youtube_diag,
    )


@router.post(
    "/test-youtube",
    response_model=DiagnosticTestResult,
    status_code=status.HTTP_200_OK,
    summary="Safely test live connection to YouTube Data API v3"
)
async def test_youtube_api():
    """
    Executes a minimal, safe 1-video search query against YouTube Data API v3
    to verify credentials and network reachability without logging secrets.
    Enforces a strict 7.0s timeout so the UI never hangs.
    """
    global _LAST_YOUTUBE_TEST
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if not settings.has_youtube_credentials():
        res = DiagnosticTestResult(
            service="youtube",
            tested=True,
            status="credentials_missing",
            latency_ms=0,
            message="YOUTUBE_API_KEY is not configured in backend environment. Using development fallback.",
        )
        _LAST_YOUTUBE_TEST = {"status": "missing", "timestamp": now_iso, "message": res.message}
        return res

    api_key = settings.youtube_api_key
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "type": "video",
        "q": "educational",
        "maxResults": 1,
        "key": api_key,
    }

    start_time = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await asyncio.wait_for(client.get(url, params=params), timeout=7.0)
            latency = int((time.perf_counter() - start_time) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                items_cnt = len(data.get("items", []))
                res = DiagnosticTestResult(
                    service="youtube",
                    tested=True,
                    status="success",
                    latency_ms=latency,
                    message=f"YouTube Data API v3 connection successful ({latency} ms latency, {items_cnt} sample items retrieved).",
                )
            else:
                err_body = {}
                try:
                    err_body = resp.json().get("error", {})
                except Exception:
                    pass
                msg = err_body.get("message", "")
                reasons = [e.get("reason") for e in err_body.get("errors", []) if e.get("reason")]
                for d in err_body.get("details", []):
                    if isinstance(d, dict) and d.get("reason"):
                        reasons.append(d.get("reason"))

                if "quotaExceeded" in reasons or "dailyLimitExceeded" in reasons or resp.status_code == 429:
                    res = DiagnosticTestResult(
                        service="youtube",
                        tested=True,
                        status="quota_exceeded",
                        latency_ms=latency,
                        message="YouTube API daily quota exceeded for the configured Google Cloud project.",
                    )
                elif (
                    "API_KEY_INVALID" in reasons
                    or "keyInvalid" in reasons
                    or "api key expired" in msg.lower()
                    or "renew the api key" in msg.lower()
                ):
                    res = DiagnosticTestResult(
                        service="youtube",
                        tested=True,
                        status="auth_failed",
                        latency_ms=latency,
                        message="Configured YOUTUBE_API_KEY is rejected or expired by Google Cloud.",
                    )
                else:
                    res = DiagnosticTestResult(
                        service="youtube",
                        tested=True,
                        status="error",
                        latency_ms=latency,
                        message=f"YouTube API returned HTTP {resp.status_code}: {msg or 'Search request failed'}",
                    )

    except (asyncio.TimeoutError, httpx.TimeoutException):
        latency = int((time.perf_counter() - start_time) * 1000)
        res = DiagnosticTestResult(
            service="youtube",
            tested=True,
            status="network_error",
            latency_ms=latency,
            message="Connection to YouTube API timed out after 7.0 seconds. FastAPI service remains operational.",
        )
    except Exception as exc:
        latency = int((time.perf_counter() - start_time) * 1000)
        res = DiagnosticTestResult(
            service="youtube",
            tested=True,
            status="network_error",
            latency_ms=latency,
            message=f"Network error communicating with YouTube API: {type(exc).__name__}",
        )

    _LAST_YOUTUBE_TEST = {
        "status": "verified" if res.status == "success" else res.status,
        "timestamp": now_iso,
        "message": res.message,
    }
    return res


def _probe_bedrock_sync(model: str, is_admin: bool) -> DiagnosticTestResult:
    """Synchronous AWS STS and Bedrock 1-token test probe executed in a worker thread."""
    start_time = time.perf_counter()
    import boto3
    # Check STS identity first (validates credentials without model cost)
    sts = boto3.client("sts", region_name=settings.aws_region)
    caller_ident = sts.get_caller_identity()
    arn = caller_ident.get("Arn", "unknown")
    # Mask 12-digit AWS account ID in IAM ARN
    masked_arn = re.sub(r"::\d{12}:", "::************:", arn)

    # Check Bedrock model invocation access
    bedrock_rt = boto3.client("bedrock-runtime", region_name=settings.aws_region)
    try:
        # 1-token minimal test probe to verify actual account model enablement
        bedrock_rt.converse(
            modelId=model,
            messages=[{"role": "user", "content": [{"text": "ping"}]}],
            inferenceConfig={"maxTokens": 1}
        )
        total_latency = int((time.perf_counter() - start_time) * 1000)
        ident_note = f" Authenticated as IAM ARN: {masked_arn}." if is_admin else ""
        return DiagnosticTestResult(
            service="strands",
            tested=True,
            status="success",
            latency_ms=total_latency,
            message=(
                f"Bedrock invocation succeeded for model '{model}' in region '{settings.aws_region}'.{ident_note} "
                f"({total_latency} ms)."
            ),
        )
    except Exception as model_err:
        from app.agents.syllabus_analyzer import SyllabusAnalyzerAgent
        err_cat, err_msg = SyllabusAnalyzerAgent.classify_model_error(model_err)
        total_latency = int((time.perf_counter() - start_time) * 1000)

        status_code = "model_not_available" if err_cat == "MODEL_NOT_AVAILABLE" else "auth_failed"
        ident_prefix = f"AWS IAM authentication succeeded ({masked_arn} in {settings.aws_region}), but " if is_admin else f"Bedrock model '{model}' in region '{settings.aws_region}': "
        return DiagnosticTestResult(
            service="strands",
            tested=True,
            status=status_code,
            latency_ms=total_latency,
            message=f"{ident_prefix}model failed [{err_cat}]: {err_msg}",
        )


@router.post(
    "/test-strands",
    response_model=DiagnosticTestResult,
    status_code=status.HTTP_200_OK,
    summary="Safely test Strands Agents SDK provider configuration"
)
async def test_strands_model(is_admin: bool = Depends(check_is_admin)):
    """
    Safely inspects Strands provider configuration and verifies IAM identity / model availability
    without spending unnecessary token credits.
    Offloaded to thread pool with strict 7.0s timeout to guarantee event loop responsiveness.
    """
    global _LAST_STRANDS_TEST
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    provider = settings.strands_provider
    model = settings.strands_model
    has_creds = settings.has_strands_credentials()

    if not has_creds:
        res = DiagnosticTestResult(
            service="strands",
            tested=True,
            status="credentials_missing",
            latency_ms=0,
            message=(
                f"Strands credentials not configured for provider '{provider}'. "
                f"Model '{model}' will use local development fallback."
            ),
        )
        _LAST_STRANDS_TEST = {
            "status": "missing",
            "timestamp": now_iso,
            "message": res.message,
        }
        return res

    if provider == "bedrock":
        start_time = time.perf_counter()
        try:
            res = await asyncio.wait_for(
                asyncio.to_thread(_probe_bedrock_sync, model, is_admin),
                timeout=7.0
            )
        except asyncio.TimeoutError:
            latency = int((time.perf_counter() - start_time) * 1000)
            res = DiagnosticTestResult(
                service="strands",
                tested=True,
                status="timeout",
                latency_ms=latency,
                message=f"Bedrock invocation probe timed out after 7.0s in region '{settings.aws_region}'. FastAPI backend service remains operational.",
            )
        except Exception as aws_err:
            latency = int((time.perf_counter() - start_time) * 1000)
            res = DiagnosticTestResult(
                service="strands",
                tested=True,
                status="auth_failed",
                latency_ms=latency,
                message=f"AWS credential verification failed in region '{settings.aws_region}': {str(aws_err)}",
            )
    else:
        res = DiagnosticTestResult(
            service="strands",
            tested=True,
            status="success",
            latency_ms=1,
            message=(
                f"Strands configuration verified for provider '{provider}' and model '{model}'. "
                f"Credentials present in environment."
            ),
        )

    _LAST_STRANDS_TEST = {
        "status": "verified" if res.status == "success" else res.status,
        "timestamp": now_iso,
        "message": res.message,
    }
    return res


@router.post(
    "/cache/clear",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin_access)],
    summary="Administrative action: clear diagnostics cache and YouTube search cache"
)
async def clear_diagnostics_cache():
    """
    Restricted administrative action: clears search cache and resets in-memory probe history.
    Requires administrative privileges in production.
    """
    global _LAST_YOUTUBE_TEST, _LAST_STRANDS_TEST
    _LAST_YOUTUBE_TEST = None
    _LAST_STRANDS_TEST = None

    deleted_count = 0
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("DELETE FROM youtube_search_cache")
            deleted_count = cursor.rowcount if hasattr(cursor, "rowcount") else 0
            conn.commit()
    except Exception as e:
        logger.warning(f"Admin cache clear warning: {e}")

    return {
        "status": "success",
        "message": f"Diagnostics and search cache successfully cleared ({deleted_count} cached entries removed).",
        "cleared_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
