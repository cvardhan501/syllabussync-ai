from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Application status")
    app_name: str = Field(description="Name of the application")
    version: str = Field(description="Application version")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Current UTC timestamp")
    environment: str = Field(description="Current deployment environment")
    database_connected: Optional[bool] = Field(default=None, description="Lightweight database connectivity status")
