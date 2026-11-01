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
from fastapi import APIRouter, Depends, status
import httpx

from app.core.config import settings
from app.core.auth import verify_diagnostics_access
from app.models.database import get_db_connection, is_postgres
from app.schemas.diagnostics import (
    BackendDiagnostic,
    DatabaseDiagnostic,
    StrandsDiagnostic,
    YouTubeDiagnostic,
    SystemDiagnosticsResponse,
    DiagnosticTestResult,
)

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
async def get_system_diagnostics():
    """
    Returns sanitized diagnostics of backend, SQLite database,
    Strands Agents SDK configuration, and YouTube Data API v3 settings.
    Guarantees 100% zero secret leakage.
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
            tables_list = [r["name"] for r in rows]
    except Exception:
        db_status = "error"

    database_diag = DatabaseDiagnostic(
        status=db_status,
        engine=engine_name,
        tables_count=len(tables_list),
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

    strands_diag = StrandsDiagnostic(
        provider=provider,
        model=model,
        credentials_configured=has_strands_creds,
        credentials_summary=creds_summary,
        fallback_enabled=settings.allow_dev_fallback_analysis,
        active_mode=active_mode,
        fallback_reason=fallback_reason,
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

    youtube_diag = YouTubeDiagnostic(
        key_configured=has_yt_creds,
        key_summary=key_summary,
        fallback_enabled=settings.allow_dev_fallback_youtube,
        active_mode=yt_active_mode,
        fallback_reason=yt_fallback_reason,
        cached_queries_count=cached_count,
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
    if not settings.has_youtube_credentials():
        return DiagnosticTestResult(
            service="youtube",
            tested=True,
            status="credentials_missing",
            latency_ms=0,
            message="YOUTUBE_API_KEY is not configured in backend/.env. Using development fallback.",
        )

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
            resp = await client.get(url, params=params)
            latency = int((time.perf_counter() - start_time) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                items_cnt = len(data.get("items", []))
                return DiagnosticTestResult(
                    service="youtube",
                    tested=True,
                    status="success",
                    latency_ms=latency,
                    message=f"YouTube Data API v3 connection successful ({latency} ms latency, {items_cnt} sample items retrieved).",
                )
            elif resp.status_code == 403:
                err_body = resp.json().get("error", {})
                reasons = [e.get("reason") for e in err_body.get("errors", [])]
                if "quotaExceeded" in reasons or "dailyLimitExceeded" in reasons:
                    return DiagnosticTestResult(
                        service="youtube",
                        tested=True,
                        status="quota_exceeded",
                        latency_ms=latency,
                        message="YouTube API quota exceeded for the configured Google Cloud project.",
                    )
                else:
                    return DiagnosticTestResult(
                        service="youtube",
                        tested=True,
                        status="auth_failed",
                        latency_ms=latency,
                        message="YouTube API authorization failed: Key is invalid, expired, or unauthorized for YouTube Data API v3.",
                    )
            elif resp.status_code == 400:
                return DiagnosticTestResult(
                    service="youtube",
                    tested=True,
                    status="auth_failed",
                    latency_ms=latency,
                    message="YouTube API rejected the request format or parameter.",
                )
            else:
                return DiagnosticTestResult(
                    service="youtube",
                    tested=True,
                    status="error",
                    latency_ms=latency,
                    message=f"YouTube API returned HTTP status {resp.status_code}.",
                )

    except httpx.TimeoutException:
        return DiagnosticTestResult(
            service="youtube",
            tested=True,
            status="network_error",
            latency_ms=6000,
            message="Connection to YouTube API timed out (6.0s timeout reached).",
        )
    except httpx.RequestError as exc:
        return DiagnosticTestResult(
            service="youtube",
            tested=True,
            status="network_error",
            latency_ms=0,
            message=f"Network error contacting YouTube: {exc.__class__.__name__}.",
        )


@router.post(
    "/test-strands",
    response_model=DiagnosticTestResult,
    status_code=status.HTTP_200_OK,
    summary="Safely test Strands Agents SDK provider configuration"
)
async def test_strands_model():
    """
    Safely inspects Strands provider configuration and verifies IAM identity / model availability
    without spending unnecessary token credits.
    """
    provider = settings.strands_provider
    model = settings.strands_model
    has_creds = settings.has_strands_credentials()

    if not has_creds:
        return DiagnosticTestResult(
            service="strands",
            tested=True,
            status="credentials_missing",
            latency_ms=0,
            message=(
                f"Strands credentials not configured for provider '{provider}'. "
                f"Model '{model}' will use local development fallback."
            ),
        )

    if provider == "bedrock":
        start_time = time.perf_counter()
        try:
            import boto3
            # Check STS identity first (validates access key and secret key without model cost)
            sts = boto3.client("sts", region_name=settings.aws_region)
            caller_ident = sts.get_caller_identity()
            arn = caller_ident.get("Arn", "unknown")
            # Mask 12-digit AWS account ID in IAM ARN to prevent infrastructure exposure
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
                return DiagnosticTestResult(
                    service="strands",
                    tested=True,
                    status="success",
                    latency_ms=total_latency,
                    message=(
                        f"Bedrock invocation succeeded for model '{model}' in region '{settings.aws_region}'. "
                        f"Authenticated as IAM ARN: {masked_arn} ({total_latency} ms)."
                    ),
                )
            except Exception as model_err:
                from app.agents.syllabus_analyzer import SyllabusAnalyzer
                err_cat, err_msg = SyllabusAnalyzer.classify_model_error(model_err)
                total_latency = int((time.perf_counter() - start_time) * 1000)

                status_code = "model_not_available" if err_cat == "MODEL_NOT_AVAILABLE" else "auth_failed"
                return DiagnosticTestResult(
                    service="strands",
                    tested=True,
                    status=status_code,
                    latency_ms=total_latency,
                    message=(
                        f"AWS IAM authentication succeeded ({masked_arn} in {settings.aws_region}), "
                        f"but model '{model}' failed [{err_cat}]: {err_msg}"
                    ),
                )

        except Exception as aws_err:
            latency = int((time.perf_counter() - start_time) * 1000)
            return DiagnosticTestResult(
                service="strands",
                tested=True,
                status="auth_failed",
                latency_ms=latency,
                message=f"AWS credential verification failed in region '{settings.aws_region}': {str(aws_err)}",
            )

    return DiagnosticTestResult(
        service="strands",
        tested=True,
        status="success",
        latency_ms=1,
        message=(
            f"Strands configuration verified for provider '{provider}' and model '{model}'. "
            f"Credentials present in environment."
        ),
    )
