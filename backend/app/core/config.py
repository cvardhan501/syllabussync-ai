from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SyllabusSync AI API"
    app_version: str = "0.1.0"
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
    
    # Future extension keys (Phase 2 & beyond)
    youtube_api_key: str | None = None
    strands_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
