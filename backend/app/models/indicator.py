"""Append-only, evidence-linked investigator assertions; never threat verdicts."""
from uuid import UUID
from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.common import RecordMixin

class IndicatorObservation(RecordMixin, Base):
    __tablename__ = 'indicator_observations'
    __table_args__ = (
        ForeignKeyConstraint(['evidence_id','incident_id'],['evidence.id','evidence.incident_id'],ondelete='RESTRICT',name='fk_indicator_evidence_incident'),
        UniqueConstraint('created_by_id','submission_id',name='uq_indicator_submission'),
        UniqueConstraint('supersedes_id',name='uq_indicator_successor'),
        CheckConstraint("kind IN ('sha256','ip','domain','filename')",name='kind'),
        CheckConstraint("source_kind = 'manual' OR (source_kind = 'evidence_sha256' AND kind = 'sha256') OR (source_kind = 'evidence_filename' AND kind = 'filename')",name='source_kind'),
        CheckConstraint('length(raw_value) BETWEEN 1 AND 255 AND length(normalized_value) BETWEEN 1 AND 255',name='value_length'),
        CheckConstraint('schema_version = 1 AND length(request_sha256) = 64',name='version_digest'),
        CheckConstraint('length(actor_label) BETWEEN 1 AND 120',name='actor_label'),
        CheckConstraint('source_locator IS NULL OR length(source_locator) BETWEEN 1 AND 512',name='locator_length'),
        Index('ix_indicator_case_created','incident_id','created_at','id'),
        Index('ix_indicator_evidence_created','evidence_id','created_at','id'),
        Index('ix_indicator_case_value','incident_id','kind','normalized_value'),
    )
    incident_id: Mapped[UUID] = mapped_column(ForeignKey('incidents.id',ondelete='RESTRICT'))
    evidence_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(String(16))
    raw_value: Mapped[str] = mapped_column(String(255))
    normalized_value: Mapped[str] = mapped_column(String(255))
    source_kind: Mapped[str] = mapped_column(String(32))
    source_locator: Mapped[str | None] = mapped_column(String(512))
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey('users.id',ondelete='RESTRICT'))
    actor_label: Mapped[str] = mapped_column(String(120))
    schema_version: Mapped[int] = mapped_column(default=1)
    submission_id: Mapped[UUID]
    request_sha256: Mapped[str] = mapped_column(String(64))
    supersedes_id: Mapped[UUID | None] = mapped_column(ForeignKey('indicator_observations.id',ondelete='RESTRICT'))

@event.listens_for(IndicatorObservation,'before_update')
@event.listens_for(IndicatorObservation,'before_delete')
def immutable_indicator(*_args):
    raise ValueError('Indicator observations are append-only')
