"""
Safe Diagnostic Schemas
=======================
Strictly redacts any secrets, authorization headers, full API keys, or raw exception traces.
Provides operational visibility into backend connectivity, Strands SDK, YouTube API, and SQLite.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class BackendDiagnostic(BaseModel):
    status: str = Field(description="Operational status ('healthy')")
    version: str = Field(description="API version")
    environment: str = Field(description="Current APP_ENV")


class DatabaseDiagnostic(BaseModel):
    status: str = Field(description="'connected' or 'error'")
    engine: str = Field(default="SQLite")
    tables_count: int = Field(default=0)
    tables: List[str] = Field(default_factory=list)


class StrandsDiagnostic(BaseModel):
    provider: str = Field(description="Configured provider (e.g. 'bedrock', 'openai', 'anthropic')")
    model: str = Field(description="Model identifier")
    region: Optional[str] = Field(default="ap-southeast-2", description="AWS region for Bedrock")
    credentials_configured: bool = Field(description="Whether required credentials exist in environment")
    credentials_summary: str = Field(description="Safe overview without secrets (e.g. 'Configured (Bedrock)')")
    fallback_enabled: bool = Field(description="Whether development fallback is enabled")
    active_mode: str = Field(description="'live' if credentials configured, else 'development_fallback'")
    fallback_reason: Optional[str] = Field(default=None)
    connectivity_status: str = Field(default="unverified", description="'verified', 'unverified', 'auth_failed', 'model_not_available', or 'missing'")
    last_tested: Optional[str] = Field(default=None, description="ISO timestamp of last live test probe")
    last_test_message: Optional[str] = Field(default=None, description="Safe summary from last test probe")


class YouTubeDiagnostic(BaseModel):
    key_configured: bool = Field(description="Whether YOUTUBE_API_KEY exists")
    key_summary: str = Field(description="Safe key representation without secrets (e.g. 'Configured (39 chars)' or 'Not Set')")
    fallback_enabled: bool = Field(description="Whether development fallback is enabled")
    active_mode: str = Field(description="'live' if key configured, else 'development_fallback'")
    fallback_reason: Optional[str] = Field(default=None)
    cached_queries_count: int = Field(default=0)
    connectivity_status: str = Field(default="unverified", description="'verified', 'unverified', 'expired_or_invalid', 'quota_exceeded', or 'missing'")
    last_tested: Optional[str] = Field(default=None, description="ISO timestamp of last live test probe")
    last_test_message: Optional[str] = Field(default=None, description="Safe summary from last test probe")


class SystemDiagnosticsResponse(BaseModel):
    status: str = Field(default="success")
    timestamp: str = Field(description="ISO timestamp of diagnostic check")
    backend: BackendDiagnostic
    database: DatabaseDiagnostic
    strands: StrandsDiagnostic
    youtube: YouTubeDiagnostic


class DiagnosticTestResult(BaseModel):
    service: str = Field(description="'youtube' or 'strands'")
    tested: bool = Field(default=True)
    status: str = Field(description="'success', 'quota_exceeded', 'auth_failed', 'network_error', 'credentials_missing', or 'error'")
    latency_ms: Optional[int] = Field(default=None)
    message: str = Field(description="Safe human-readable summary (strictly zero secret tokens)")

