from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SyllabusSync AI API"
    app_version: "str" = "0.2.0"
    app_env: str = "development"
    api_port: int = 8000
    api_host: str = "0.0.0.0"
    
    # CORS Configuration
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    # Upload limits
    max_upload_size_mb: int = 10
    
    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    # Database
    database_url: str = "sqlite:///./syllabus_sync.db"
    
    # Strands Agents SDK Configuration
    strands_provider: str = "bedrock"
    strands_model: str = "bedrock/us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    # AWS Bedrock Credentials
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
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
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
