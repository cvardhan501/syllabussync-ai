import os
import json
from pathlib import Path
from typing import List, Optional, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "SyllabusSync AI API"
    app_version: str = "0.2.0"
    app_env: str = "development"
    api_port: int = 8000
    api_host: str = "0.0.0.0"

    @property
    def is_production(self) -> bool:
        """Determines if running in a strict production environment."""
        return self.app_env.strip().lower() in ("production", "prod")

    @property
    def is_development(self) -> bool:
        """Determines if running in local development mode."""
        return self.app_env.strip().lower() in ("development", "dev", "local")

    @property
    def is_testing(self) -> bool:
        """Determines if running in automated test mode."""
        return self.app_env.strip().lower() in ("test", "testing")

    # Supabase Auth Configuration (JWT verification readiness)
    supabase_jwt_secret: Optional[str] = None
    supabase_project_url: Optional[str] = "https://qdlnupgdtgmhvkknjmlv.supabase.co"
    supabase_jwks_url: Optional[str] = None
    admin_api_key: Optional[str] = None

    @property
    def effective_jwks_url(self) -> str:
        """Calculates the active Supabase JWKS endpoint for public key retrieval."""
        if self.supabase_jwks_url and self.supabase_jwks_url.strip():
            return self.supabase_jwks_url.strip()
        base = (self.supabase_project_url or "https://qdlnupgdtgmhvkknjmlv.supabase.co").strip().rstrip("/")
        return f"{base}/auth/v1/.well-known/jwks.json"

    @property
    def expected_jwt_issuer(self) -> str:
        """Expected Supabase JWT issuer URL."""
        base = (self.supabase_project_url or "https://qdlnupgdtgmhvkknjmlv.supabase.co").strip().rstrip("/")
        return f"{base}/auth/v1"
    
    # CORS Configuration
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://syllabussync-ai.vercel.app",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        origins: List[str] = []
        if isinstance(v, str):
            v_str = v.strip()
            if v_str:
                if v_str.startswith("[") and v_str.endswith("]"):
                    try:
                        parsed = json.loads(v_str)
                        if isinstance(parsed, list):
                            origins = [str(o).strip() for o in parsed if str(o).strip()]
                    except Exception:
                        pass
                if not origins:
                    origins = [origin.strip() for origin in v_str.split(",") if origin.strip()]
        elif isinstance(v, (list, tuple, set)):
            origins = [str(origin).strip() for origin in v if str(origin).strip()]
        elif v:
            origins = [str(v).strip()]

        # Guarantee production domain is included alongside configured origins
        prod_origin = "https://syllabussync-ai.vercel.app"
        if prod_origin not in origins:
            origins.append(prod_origin)

        return origins
    
    # Upload limits (aligned with Vercel 4.5 MB request payload limit)
    max_upload_size_mb: float = 4.5
    
    @property
    def max_upload_size_bytes(self) -> int:
        return int(self.max_upload_size_mb * 1024 * 1024)

    # Database
    database_url: str = "sqlite:///./syllabus_sync.db"
    
    # Strands Agents SDK Configuration
    strands_provider: str = "bedrock"
    strands_model: str = "amazon.nova-lite-v1:0"
    strands_streaming: Optional[bool] = None
    
    # AWS Bedrock Credentials
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "ap-southeast-2"
    aws_session_token: Optional[str] = None
    
    # Alternative Provider Credentials
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Development Fallback Flag (for local UI development when keys are not configured)
    allow_dev_fallback_analysis: bool = True

    # Future extension keys (Phase 3 & beyond)
    youtube_api_key: Optional[str] = None
    youtube_max_search_results: int = 5
    youtube_cache_ttl_hours: int = 48
    allow_dev_fallback_youtube: bool = True

    def has_youtube_credentials(self) -> bool:
        """Determines if YouTube Data API credentials are configured."""
        return bool(self.youtube_api_key and self.youtube_api_key.strip())

    def has_strands_credentials(self) -> bool:
        """Determines if the active provider has valid credentials configured."""
        provider = self.strands_provider.lower()
        if provider == "bedrock":
            return bool(self.aws_access_key_id and self.aws_secret_access_key)
        elif provider == "openai":
            return bool(self.openai_api_key)
        elif provider == "anthropic":
            return bool(self.anthropic_api_key)
        elif provider in ("ollama", "local"):
            return True
        return False

    model_config = SettingsConfigDict(
        env_file=(
            str(BACKEND_DIR / ".env"),
            str(ROOT_DIR / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure AWS credentials from .env are exported into os.environ
# so that boto3/botocore default session picks them up without triggering SSO login provider
if settings.aws_access_key_id and "AWS_ACCESS_KEY_ID" not in os.environ:
    os.environ["AWS_ACCESS_KEY_ID"] = settings.aws_access_key_id
if settings.aws_secret_access_key and "AWS_SECRET_ACCESS_KEY" not in os.environ:
    os.environ["AWS_SECRET_ACCESS_KEY"] = settings.aws_secret_access_key
if settings.aws_region and "AWS_REGION" not in os.environ:
    os.environ["AWS_REGION"] = settings.aws_region
    os.environ["AWS_DEFAULT_REGION"] = settings.aws_region
if settings.aws_session_token and "AWS_SESSION_TOKEN" not in os.environ:
    os.environ["AWS_SESSION_TOKEN"] = settings.aws_session_token

