"""Verified collection metadata; legacy Phase 1 records remain distinguishable."""

from uuid import UUID
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base
from app.models.common import RecordMixin, UTCDateTime


class Evidence(RecordMixin, Base):
    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="nonnegative_size"),
        CheckConstraint("length(sha256) = 64", name="sha256_length"),
        UniqueConstraint("collection_job_id", "collection_item_id", name="uq_evidence_job_item"),
        ForeignKeyConstraint(["collection_job_id", "incident_id"],
                             ["collection_jobs.id", "collection_jobs.incident_id"],
                             name="fk_evidence_job_incident", ondelete="RESTRICT"),
        CheckConstraint("verification_status IN ('legacy', 'verified')", name="verification_status"),
        CheckConstraint("(collection_job_id IS NULL AND collection_item_id IS NULL AND verification_status = 'legacy') OR "
                        "(collection_job_id IS NOT NULL AND collection_item_id IS NOT NULL AND source_path IS NOT NULL "
                        "AND collected_at IS NOT NULL AND verified_at IS NOT NULL AND verification_status = 'verified')",
                        name="collection_provenance"),
        CheckConstraint("review_state IN ('unreviewed', 'in_review', 'reviewed')", name="review_state"),
        CheckConstraint("metadata_revision >= 0 AND custody_sequence >= 0", name="nonnegative_revisions"),
        CheckConstraint("(custody_sequence = 0 AND custody_head_hash IS NULL) OR "
                        "(custody_sequence > 0 AND custody_head_hash IS NOT NULL AND length(custody_head_hash) = 64)",
                        name="custody_head"),
        Index("ix_evidence_incident_created_id", "incident_id", "created_at", "id"),
        Index("ix_evidence_review_state", "review_state"),
        Index("uq_evidence_id_incident", "id", "incident_id", unique=True),
    )

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id", ondelete="RESTRICT"), index=True)
    collected_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(127), default="application/octet-stream")
    size_bytes: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    collection_job_id: Mapped[UUID | None]
    collection_item_id: Mapped[UUID | None]
    source_path: Mapped[str | None] = mapped_column(String(1024))
    collected_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    verification_status: Mapped[str] = mapped_column(String(16), default="legacy", server_default="legacy")
    display_title: Mapped[str | None] = mapped_column(String(200))
    review_state: Mapped[str] = mapped_column(String(16), default="unreviewed", server_default="unreviewed")
    metadata_revision: Mapped[int] = mapped_column(default=0, server_default="0")
    custody_sequence: Mapped[int] = mapped_column(default=0, server_default="0")
    custody_head_hash: Mapped[str | None] = mapped_column(String(64))
    incident: Mapped["Incident"] = relationship(back_populates="evidence")
    collected_by: Mapped["User"] = relationship()

    @validates("sha256")
    def validate_digest(self, _key: str, value: str) -> str:
        normalized = value.lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("sha256 must contain exactly 64 hexadecimal characters")
        return normalized
