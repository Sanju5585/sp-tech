from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "School Timetable Generator"
    app_env: str = "development"
    secret_key: str = "change-this-to-a-long-random-secret"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    bootstrap_super_username: str = "superAdmin"
    bootstrap_super_email: str = "superadmin@sanjivani.app"
    bootstrap_super_password: str = "sanjeev@5585"
    portal_sso_secret: str = "sanjivani-portal-sso-change-me"
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:8080,http://127.0.0.1:8080,"
        "http://localhost:8000,http://127.0.0.1:8000,"
        "https://sanjivani.com,https://www.sanjivani.com,"
        "https://sanjivanione.com,https://www.sanjivanione.com,"
        "https://sanjivanione.in,https://www.sanjivanione.in,"
        "https://127.0.0.1,https://localhost"
    )
    database_url: str = "sqlite:///./timetable.db"
    gemini_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "gemini_api_key",
            "google_api_key",
        ),
    )
    gemini_model: str = "gemini-2.5-flash-lite"
    solver_max_time_seconds: int = 40
    solver_num_workers: int = 8

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
