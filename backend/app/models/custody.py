"""Attributed, append-only application history; database administrators remain trusted."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import CheckConstraint, ForeignKey, JSON, String, UniqueConstraint, Uuid, event
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.common import UTCDateTime, utc_now


class CustodyEvent(Base):
    __tablename__ = "custody_events"
    __table_args__ = (
        UniqueConstraint("evidence_id", "sequence", name="uq_custody_evidence_sequence"),
        UniqueConstraint("evidence_id", "operation_id", "event_type", name="uq_custody_operation_type"),
        CheckConstraint("sequence > 0 AND schema_version = 1", name="sequence_version"),
        CheckConstraint("length(event_hash) = 64 AND (previous_hash IS NULL OR length(previous_hash) = 64)", name="hash_lengths"),
        CheckConstraint("(actor_type = 'user' AND actor_user_id IS NOT NULL AND actor_agent_id IS NULL AND system_actor IS NULL) OR "
                        "(actor_type = 'agent' AND actor_agent_id IS NOT NULL AND actor_user_id IS NULL AND system_actor IS NULL) OR "
                        "(actor_type = 'system' AND system_actor IS NOT NULL AND actor_user_id IS NULL AND actor_agent_id IS NULL)", name="actor_identity"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    evidence_id: Mapped[UUID] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    sequence: Mapped[int]
    schema_version: Mapped[int] = mapped_column(default=1, server_default="1")
    event_type: Mapped[str] = mapped_column(String(64))
    actor_type: Mapped[str] = mapped_column(String(16))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    actor_agent_id: Mapped[UUID | None] = mapped_column(ForeignKey("agents.id", ondelete="RESTRICT"))
    system_actor: Mapped[str | None] = mapped_column(String(64))
    actor_label: Mapped[str] = mapped_column(String(120))
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    source_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    operation_id: Mapped[UUID] = mapped_column(Uuid)
    details: Mapped[dict] = mapped_column(JSON)
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64))


@event.listens_for(CustodyEvent, "before_update")
@event.listens_for(CustodyEvent, "before_delete")
def immutable_custody(_mapper, _connection, _target):
    raise ValueError("Custody events cannot be updated or deleted through the ORM")
