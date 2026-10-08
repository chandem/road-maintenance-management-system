from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the AI-RMMS backend.

    Point these values at the dedicated AI-RMMS Supabase project
    (eu-west-1, database: ai-rmms). Never commit real secrets.
    """

    # Required — AI-RMMS Supabase project
    supabase_url: str
    supabase_publishable_key: str

    # Optional — server-side only; never expose to the browser or frontend
    supabase_service_role_key: str | None = None

    # AI provider
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "text-embedding-004"

    # Optional labels for ops / health reporting
    supabase_project_ref: str | None = None
    supabase_region: str = "eu-west-1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_publishable_key)

    @property
    def has_service_role(self) -> bool:
        return bool(self.supabase_service_role_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
