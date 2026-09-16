"""Observed event time is distinct from the record creation time."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, String, Text, UniqueConstraint, event, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import RecordMixin, UTCDateTime


class TimelineEvent(RecordMixin, Base):
    __tablename__ = "timeline_events"
    __table_args__ = (
        Index("ix_timeline_events_incident_occurred", "incident_id", "occurred_at"),
        Index("ix_timeline_incident_occurred_id", "incident_id", "occurred_at", "id"),
        Index("ix_timeline_evidence_occurred_id", "evidence_id", "occurred_at", "id"),
        ForeignKeyConstraint(['evidence_id', 'incident_id'], ['evidence.id', 'evidence.incident_id'],
                             name='fk_timeline_evidence_incident', ondelete='RESTRICT'),
        UniqueConstraint('recorded_by_id', 'submission_id', name='uq_timeline_recorder_submission'),
        CheckConstraint("origin IN ('legacy', 'investigator')", name='origin'),
        CheckConstraint("origin = 'legacy' OR (evidence_id IS NOT NULL AND reported_time IS NOT NULL "
                        "AND recorded_by_label IS NOT NULL AND submission_id IS NOT NULL "
                        "AND request_sha256 IS NOT NULL AND length(request_sha256) = 64)", name='provenance'),
    )

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id", ondelete="RESTRICT"))
    recorded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime())
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(200))
    evidence_id: Mapped[UUID | None]
    origin: Mapped[str] = mapped_column(String(16), default='legacy', server_default='legacy')
    reported_time: Mapped[str | None] = mapped_column(String(64))
    source_locator: Mapped[str | None] = mapped_column(String(512))
    recorded_by_label: Mapped[str | None] = mapped_column(String(120))
    submission_id: Mapped[UUID | None]
    request_sha256: Mapped[str | None] = mapped_column(String(64))
    incident: Mapped["Incident"] = relationship(back_populates="timeline_events")
    recorded_by: Mapped["User"] = relationship()


@event.listens_for(TimelineEvent, 'before_update')
@event.listens_for(TimelineEvent, 'before_delete')
def immutable_observation(_mapper, connection, target):
    # Check persisted origin as well: assigning to an expired attribute must not bypass the guard.
    if target.origin == 'investigator' or connection.scalar(
        select(TimelineEvent.__table__.c.origin).where(TimelineEvent.__table__.c.id == target.id)
    ) == 'investigator':
        raise ValueError('Investigator timeline observations are append-only')
