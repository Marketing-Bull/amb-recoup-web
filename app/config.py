from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""
    # JWT secret used to verify Supabase-issued session tokens locally.
    # Found in Supabase Dashboard > Project Settings > API > JWT Settings.
    supabase_jwt_secret: str = ""
    app_secret: str = "change-this-secret"
    admin_email: str = "admin@example.com"
    app_name: str = "AMB Recoup"
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "RECOUP_"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
