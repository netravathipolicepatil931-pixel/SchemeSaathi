
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.config import settings
from backend.database import init_db
from backend.supabase_client import supabase

from backend.routers import (
    schemes_router,
    bookmarks_router,
    checklist_router,
    assistant_router,
    translations_router,
    auth_router,
    documents_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)


# Register existing API routers
app.include_router(schemes_router)
app.include_router(bookmarks_router)
app.include_router(checklist_router)
app.include_router(assistant_router)
app.include_router(translations_router)
app.include_router(auth_router)
app.include_router(documents_router)


@app.get("/health", tags=["System"])
@app.get("/api/health", tags=["System"])
def health_check():
    """
    Check Supabase connection and count available schemes.
    """
    try:
        response = (
            supabase.table("schemes")
            .select("id", count="exact")
            .execute()
        )

        count = response.count
        if count is None:
            count = len(response.data or [])

        db_healthy = True

    except Exception:
        count = 0
        db_healthy = False

    return {
        "status": "healthy" if db_healthy else "degraded",
        "app": settings.app_name,
        "version": settings.version,
        "database": "connected" if db_healthy else "error",
        "total_schemes_active": count,
        "supported_languages": settings.supported_languages,
    }


# Serve frontend
FRONTEND_FILE = (
    Path(__file__).resolve().parent.parent / "index.html"
)


@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
async def serve_frontend():
    if FRONTEND_FILE.exists():
        return FileResponse(
            FRONTEND_FILE,
            media_type="text/html"
        )

    return JSONResponse({
        "message": (
            "SchemeSaathi API is running. "
            "Visit /docs for API documentation."
        )
    })


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
