from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HomeVault API"
    database_url: str = "sqlite:///./homevault.db"
    secret_key: str = "dev-secret-change-before-production"
    access_token_minutes: int = 480
    admin_username: str = "admin"
    admin_password: str = "ChangeMe123!"
    upload_dir: str = "uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HOMEVAULT_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
