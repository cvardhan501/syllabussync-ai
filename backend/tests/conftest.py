"""
Pytest configuration for SyllabusSync AI backend test suite.
Ensures unit tests run against local SQLite database without network access.
"""

import os
import pytest
from app.core.config import settings

# Force SQLite and local development environment for automated test execution
settings.database_url = "sqlite:///./syllabus_sync.db"
settings.app_env = "development"
settings.youtube_api_key = ""
os.environ["YOUTUBE_API_KEY"] = ""
