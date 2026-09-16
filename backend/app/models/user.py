"""Investigator identity; plaintext passwords must never be persisted."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base
from app.models.common import RecordMixin


class User(RecordMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    @validates("email")
    def normalize_email(self, _key: str, value: str) -> str:
        return value.strip().lower()
