"""Validated configuration; environment variables override backend/.env."""

from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SHADOWVAULT_",
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="ShadowVault AI", min_length=1)
    environment: Literal["development", "test", "production"] = "development"
    database_url: SecretStr = SecretStr(
        f"sqlite:///{(BACKEND_DIR / 'shadowvault.db').as_posix()}"
    )
    operator_user_id: UUID | None = None
    operator_token_sha256: SecretStr | None = None
    # No model or destination is selected by these settings. The adapter is
    # administrator-reviewed executable code, never supplied by an API caller.
    ai_enabled: bool = False
    ai_adapter_script: Path | None = None
    ai_provider_api_key: SecretStr | None = None
    ai_min_interval_seconds: float = Field(default=5, ge=0, le=3600)
    ai_max_per_minute: int = Field(default=6, ge=1, le=60)
    ai_max_attempts: int = Field(default=96, ge=1, le=96)
    agent_token_hours: int = Field(default=24, ge=1, le=720)
    evidence_dir: Path = BACKEND_DIR / "var" / "evidence"
    max_upload_bytes: int = Field(default=100 * 1024 * 1024, ge=1, le=1024 * 1024 * 1024)
    max_job_bytes: int = Field(default=500 * 1024 * 1024, ge=1)
    upload_timeout_seconds: int = Field(default=120, ge=1, le=3600)
    max_concurrent_uploads: int = Field(default=4, ge=1, le=32)
    retrieval_dir: Path = BACKEND_DIR / "var" / "retrieval"
    max_retrieval_bytes: int = Field(default=100 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)
    retrieval_timeout_seconds: int = Field(default=120, ge=1, le=3600)
    max_concurrent_retrievals: int = Field(default=2, ge=1, le=8)

    @field_validator("operator_token_sha256")
    @classmethod
    def validate_operator_digest(cls, value):
        if value is not None:
            digest = value.get_secret_value()
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Operator token SHA256 must be 64 lowercase hexadecimal characters")
        return value
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        try:
            make_url(value.get_secret_value())
        except Exception:
            raise ValueError("DATABASE_URL must be a valid SQLAlchemy URL") from None
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        from urllib.parse import urlsplit

        for value in values:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths")
        return values
