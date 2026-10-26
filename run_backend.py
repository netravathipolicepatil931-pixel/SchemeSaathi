"""
SchemeSaathi Server Entrypoint
Usage:
    python run_backend.py
or:
    uvicorn backend.main:app --reload --port 8000
"""
import os
import sys

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    from backend.config import settings
    from backend.database import init_db

    print("=" * 60)
    print(f"  Starting {settings.app_name} v{settings.version}")
    print(f"  Target: http://localhost:{settings.port}")
    print(f"  Swagger Docs: http://localhost:{settings.port}/docs")
    print(f"  ReDoc: http://localhost:{settings.port}/redoc")
    print("=" * 60)

    # Initialize SQLite database
    init_db()

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=False,
        log_level="info",
    )
