from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class MkDatabaseSettings(BaseSettings):
    """Configuração opcional e isolada do PostgreSQL externo do MK."""

    mk_db_host: str | None = None
    mk_db_port: int = 5432
    mk_db_name: str | None = None
    mk_db_user: str | None = None
    mk_db_password: SecretStr | None = None
    mk_db_sslmode: Literal["disable", "require", "verify-ca", "verify-full"] = (
        "require"
    )
    mk_db_connect_timeout_seconds: int = 5
    mk_db_statement_timeout_ms: int = 15_000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
