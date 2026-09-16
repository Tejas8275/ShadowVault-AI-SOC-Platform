"""Investigator annotations are separate from immutable acquisition facts."""
from uuid import UUID
from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.common import RecordMixin


class EvidenceNote(RecordMixin, Base):
    __tablename__ = "evidence_notes"
    __table_args__ = (
        CheckConstraint("length(body) BETWEEN 1 AND 10000", name="body_length"),
        Index("ix_evidence_notes_evidence_created_id", "evidence_id", "created_at", "id"),
    )
    evidence_id: Mapped[UUID] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    author_label: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)


class EvidenceTag(Base):
    __tablename__ = "evidence_tags"
    __table_args__ = (
        CheckConstraint("length(tag) BETWEEN 1 AND 64", name="tag_length"),
        Index("ix_evidence_tags_tag_evidence", "tag", "evidence_id"),
    )
    evidence_id: Mapped[UUID] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"), primary_key=True)
    tag: Mapped[str] = mapped_column(String(64), primary_key=True)


@event.listens_for(EvidenceNote, "before_update")
@event.listens_for(EvidenceNote, "before_delete")
def immutable_note(_mapper, _connection, _target):
    raise ValueError("Notes are append-only; add a correction as a new note")
