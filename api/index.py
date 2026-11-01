"""
Vercel Serverless Function Entry Point for SyllabusSync AI Backend API.
Mounts FastAPI ASGI application with sys.path properly configured.
"""

import sys
from pathlib import Path

# Ensure backend directory is in sys.path so 'app.*' imports resolve cleanly
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app

# Vercel's Python runtime natively detects ASGI 'app'
__all__ = ["app"]
