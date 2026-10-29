"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Sentinel default. Signing JWTs with this in production would let anyone forge
# tokens, so we refuse to boot with it outside development.
INSECURE_SECRET = "change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg2://lakas:lakas@localhost:5432/lakasmarket"

    # Auth
    secret_key: str = INSECURE_SECRET
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # AI / Specs Guard
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # App
    environment: str = "development"

    @model_validator(mode="after")
    def _require_secret_outside_dev(self) -> "Settings":
        if self.environment != "development" and self.secret_key == INSECURE_SECRET:
            raise ValueError(
                "SECRET_KEY must be set to a strong random value when "
                f"ENVIRONMENT={self.environment!r} (refusing to use the insecure default)."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
