"""
SyllabusSync AI — Backend Entrypoint for Vercel Services.
Exposes the ASGI FastAPI application 'app' directly from the backend root directory.
"""

import sys
from pathlib import Path

# Ensure backend root directory is in sys.path so 'app.*' imports resolve cleanly
BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    # Use SelectorEventLoop on Windows to prevent WinError 64 IOCP socket crashes when clients reset connections
    loop_target = "asyncio:SelectorEventLoop" if sys.platform == "win32" else "auto"
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, loop=loop_target, reload=False)


