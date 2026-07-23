import httpx
from supabase import create_client, Client
from functools import lru_cache
from app.config import get_settings


@lru_cache()
def get_supabase() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)


def get_supabase_admin() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)


async def get_current_user_from_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        supabase = get_supabase()
        supabase.auth.set_session(token, "")
        response = await supabase.auth.get_user()
        return response.user if response else None
    except Exception:
        return None
