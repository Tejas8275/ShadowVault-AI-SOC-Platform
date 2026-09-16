"""Operator-enrolled collector identity. Only token digests are persisted."""
from datetime import datetime
from uuid import UUID
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.common import RecordMixin, UTCDateTime


class Agent(RecordMixin, Base):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(120))
    platform: Mapped[str] = mapped_column(String(32), default="windows")
    collector_version: Mapped[str] = mapped_column(String(32))
    registered_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    token_sha256: Mapped[str] = mapped_column(String(64), unique=True)
    token_expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
