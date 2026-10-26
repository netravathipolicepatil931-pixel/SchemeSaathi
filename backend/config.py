
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from SchemeSaathi/.env
load_dotenv(BASE_DIR / ".env")


class Settings(BaseModel):
    app_name: str = "SchemeSaathi API"
    app_description: str = (
        "AI-powered platform helping citizens discover government schemes, "
        "check eligibility, get personalized document checklists, and access "
        "multilingual application guidance with verified official links."
    )
    version: str = "1.0.0"

    debug: bool = os.getenv("DEBUG", "False").lower() in (
        "true", "1", "yes"
    )
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # Existing SQLite configuration (fallback)
    db_path: str = os.getenv(
        "DATABASE_PATH",
        str(BASE_DIR / "schemesaathi.db")
    )

    # Supabase configuration
    supabase_url: str | None = os.getenv("SUPABASE_URL") or None
    supabase_key: str | None = os.getenv("SUPABASE_KEY") or None
    supabase_secret_key: str | None = os.getenv("SUPABASE_SECRET_KEY") or None

    # PostgreSQL connection string (for future migration)
    database_url: str | None = os.getenv("DATABASE_URL") or None

    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None

    cors_origins: list[str] = [
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5500",
        "null",
        "*"
    ]

    supported_languages: list[str] = ["en", "kn", "hi"]
    default_language: str = "en"


settings = Settings()
