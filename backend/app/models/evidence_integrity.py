"""Durable integrity-check structure only; execution is outside Phase 2B-1."""
from datetime import datetime
from uuid import UUID
from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.common import RecordMixin, UTCDateTime


class EvidenceIntegrityCheck(RecordMixin, Base):
    __tablename__ = "evidence_integrity_checks"
    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name="status"),
        CheckConstraint("result IS NULL OR result IN ('matches', 'mismatch', 'missing', 'unavailable')", name="result"),
        CheckConstraint("expected_size_bytes >= 0 AND attempts >= 0 AND (observed_size_bytes IS NULL OR observed_size_bytes >= 0)", name="nonnegative_values"),
        CheckConstraint("length(expected_sha256) = 64 AND (observed_sha256 IS NULL OR length(observed_sha256) = 64)", name="digest_lengths"),
        CheckConstraint("(status IN ('queued', 'running') AND result IS NULL AND completed_at IS NULL) OR "
                        "(status IN ('completed', 'failed') AND result IS NOT NULL AND completed_at IS NOT NULL)", name="completion"),
        Index("ix_integrity_evidence_created_id", "evidence_id", "created_at", "id"),
        Index("ix_integrity_status_created", "status", "created_at"),
    )
    evidence_id: Mapped[UUID] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    requested_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(16), default="queued", server_default="queued")
    result: Mapped[str | None] = mapped_column(String(16))
    expected_sha256: Mapped[str] = mapped_column(String(64))
    expected_size_bytes: Mapped[int]
    observed_sha256: Mapped[str | None] = mapped_column(String(64))
    observed_size_bytes: Mapped[int | None]
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    lease_token: Mapped[UUID | None]
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(64))
