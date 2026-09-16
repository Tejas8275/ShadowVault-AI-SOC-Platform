"""Case management history, independent of evidence custody."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import CheckConstraint, ForeignKey, JSON, String, UniqueConstraint, Uuid, event
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.common import UTCDateTime


class CaseHistoryEvent(Base):
    __tablename__ = 'case_history_events'
    __table_args__ = (
        UniqueConstraint('incident_id', 'revision', name='uq_case_history_incident_revision'),
        CheckConstraint('revision >= 0 AND schema_version = 1', name='revision_version'),
        CheckConstraint("(event_type = 'baseline_registered' AND actor_type = 'system' AND actor_user_id IS NULL AND system_actor IS NOT NULL AND system_actor = 'migration:0007' AND source = 'migration') OR "
                        "(event_type IN ('case_created','case_updated') AND actor_type = 'user' AND actor_user_id IS NOT NULL AND system_actor IS NULL AND source IN ('api','trusted_cli'))", name='event_actor'),
        CheckConstraint("event_type != 'case_created' OR revision = 0", name='creation_revision'),
        CheckConstraint("event_type != 'case_updated' OR revision >= 1", name='update_revision'),
        CheckConstraint('length(actor_label) BETWEEN 1 AND 120', name='actor_label'),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey('incidents.id', ondelete='RESTRICT'))
    revision: Mapped[int]
    event_type: Mapped[str] = mapped_column(String(32))
    schema_version: Mapped[int] = mapped_column(default=1)
    actor_type: Mapped[str] = mapped_column(String(16))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    actor_label: Mapped[str] = mapped_column(String(120))
    system_actor: Mapped[str | None] = mapped_column(String(32))
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime())
    changes: Mapped[dict] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(16))


@event.listens_for(CaseHistoryEvent, 'before_update')
@event.listens_for(CaseHistoryEvent, 'before_delete')
def immutable_history(_mapper, _connection, _target):
    raise ValueError('Case history is append-only')
