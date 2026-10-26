
from supabase import create_client, Client
from backend.config import settings


def get_supabase_client() -> Client:
    """Client for publicly readable government schemes."""

    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError(
            "SUPABASE_URL or SUPABASE_KEY is missing from .env"
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_key
    )


def get_supabase_admin_client() -> Client:
    """Privileged client for trusted backend operations only."""

    if not settings.supabase_url or not settings.supabase_secret_key:
        raise ValueError(
            "SUPABASE_URL or SUPABASE_SECRET_KEY is missing from .env"
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key
    )


# Existing public client
supabase = get_supabase_client()

# Backend-only client
supabase_admin = get_supabase_admin_client()
