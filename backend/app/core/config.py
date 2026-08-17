"""
Central application configuration.
All environment-specific / store-specific values live here (never hardcoded
elsewhere in the app), loaded from environment variables / .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://talagang:change_me@localhost:5432/talagang_pos"

    # Auth
    JWT_SECRET_KEY: str = "insecure-dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720  # 12 hours - employees shouldn't re-login mid-shift

    # Store identity (configurable, never hardcoded in templates/receipts)
    STORE_NAME: str = "TALAGANG CASH & CARRY"
    STORE_ADDRESS: str = "Talagang, Punjab, Pakistan"
    STORE_PHONE: str = ""
    DEFAULT_CURRENCY: str = "PKR"

    # Business rules
    ALLOW_NEGATIVE_STOCK: bool = False
    LOW_STOCK_DEFAULT: int = 15

    # App
    ENVIRONMENT: str = "development"

    # Seed (Phase 1 bootstrap only — actually read via os.getenv() in
    # seed.py, not through this settings object; kept here only for
    # documentation/discoverability of what seed.py accepts). Defaults
    # intentionally reference no specific person's name.
    SEED_ADMIN_USERNAME: str = "owner"
    SEED_ADMIN_PASSWORD: str = "change_me_immediately"
    SEED_ADMIN_FULL_NAME: str = "owner"
    SEED_EMPLOYEE_USERNAME: str = "employee"
    SEED_EMPLOYEE_PASSWORD: str = "change_me_too"
    SEED_EMPLOYEE_FULL_NAME: str = "employee"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
