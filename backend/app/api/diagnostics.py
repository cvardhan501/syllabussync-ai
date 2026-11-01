"""
System Diagnostics API
======================
Safe configuration status endpoints:
- Never reveals secret keys, passwords, authorization tokens, or full exception traces.
- Verifies database connectivity, Strands SDK provider status, and YouTube Data API v3.
- Provides interactive test endpoints for live verification.
"""

import re
import time
import datetime
import logging
from typing import Optional
from fastapi import APIRouter, Depends, status
import httpx

from app.core.config import settings
from app.core.auth import verify_diagnostics_access, check_is_admin, require_admin_access
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
    Accessible to authenticated users in production.
    Zero secret leakage guaranteed.
    """
    # 1. Backend info
    backend_diag = BackendDiagnostic(
        status="healthy",
        version=settings.app_version,
        environment=settings.app_env,
    )

    # 2. Database connectivity
    tables_list = []
    db_status = "connected"
    engine_name = "PostgreSQL" if is_postgres() else "SQLite"
    actual_tables_count = 0
    try:
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
            # Table inventory is restricted to administrators; general authenticated users see count
            tables_list = all_tables if is_admin else []
    except Exception as db_err:
        logger.warning(f"Database diagnostics probe error: {db_err}")
        db_status = "error"

    database_diag = DatabaseDiagnostic(
        status=db_status,
        engine=engine_name,
        tables_count=actual_tables_count,
        tables=tables_list,
    )

    # 3. Strands Agents SDK
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
    strands_diag = StrandsDiagnostic(
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

    # 4. YouTube Data API v3
    has_yt_creds = settings.has_youtube_credentials()
    cached_count = 0
    try:
        with get_db_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM youtube_search_cache").fetchone()
            if row:
                cached_count = row["cnt"]
    except Exception:
        pass

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
    youtube_diag = YouTubeDiagnostic(
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
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)
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
                        message="YouTube API key is expired or invalid in Google Cloud Console. Please renew YOUTUBE_API_KEY.",
                    )
                elif resp.status_code == 403:
                    res = DiagnosticTestResult(
                        service="youtube",
                        tested=True,
                        status="auth_failed",
                        latency_ms=latency,
                        message=f"YouTube API authorization failed: {msg or 'Access forbidden for YouTube Data API v3'}.",
                    )
                elif resp.status_code == 400:
                    res = DiagnosticTestResult(
                        service="youtube",
                        tested=True,
                        status="auth_failed",
                        latency_ms=latency,
                        message=f"YouTube API rejected request format or key parameter: {msg or 'Bad Request'}.",
                    )
                else:
                    res = DiagnosticTestResult(
                        service="youtube",
                        tested=True,
                        status="error",
                        latency_ms=latency,
                        message=f"YouTube API returned HTTP status {resp.status_code}.",
                    )

    except httpx.TimeoutException:
        res = DiagnosticTestResult(
            service="youtube",
            tested=True,
            status="network_error",
            latency_ms=8000,
            message="Connection to YouTube API timed out (8.0s timeout reached).",
        )
    except httpx.RequestError as exc:
        res = DiagnosticTestResult(
            service="youtube",
            tested=True,
            status="network_error",
            latency_ms=0,
            message=f"Network error contacting YouTube: {exc.__class__.__name__}.",
        )

    _LAST_YOUTUBE_TEST = {
        "status": "verified" if res.status == "success" else res.status,
        "timestamp": now_iso,
        "message": res.message,
    }
    return res


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
    Accessible to authenticated users; administrative identity details are restricted.
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
            import boto3
            # Check STS identity first (validates access key and secret key without model cost)
            sts = boto3.client("sts", region_name=settings.aws_region)
            caller_ident = sts.get_caller_identity()
            arn = caller_ident.get("Arn", "unknown")
            # Mask 12-digit AWS account ID in IAM ARN
            masked_arn = re.sub(r"::\d{12}:", "::************:", arn)
            latency = int((time.perf_counter() - start_time) * 1000)

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
                res = DiagnosticTestResult(
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
                res = DiagnosticTestResult(
                    service="strands",
                    tested=True,
                    status=status_code,
                    latency_ms=total_latency,
                    message=f"{ident_prefix}model failed [{err_cat}]: {err_msg}",
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
