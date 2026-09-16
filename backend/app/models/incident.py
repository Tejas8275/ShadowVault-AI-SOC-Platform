"""An investigation groups evidence and timeline events."""

from enum import Enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Enum as SQLEnum, ForeignKey, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import RecordMixin, UTCDateTime, utc_now


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    CLOSED = "closed"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def enum_column(enum_type, name):
    return SQLEnum(
        enum_type, name=name, native_enum=False, create_constraint=True,
        validate_strings=True, values_callable=lambda cls: [item.value for item in cls],
    )


class Incident(RecordMixin, Base):
    __tablename__ = "incidents"

    title: Mapped[str] = mapped_column(String(200))
    revision: Mapped[int] = mapped_column(default=0, server_default='0')
    updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[IncidentStatus] = mapped_column(
        enum_column(IncidentStatus, "incident_status"), default=IncidentStatus.OPEN
    )
    severity: Mapped[Severity] = mapped_column(
        enum_column(Severity, "incident_severity"), default=Severity.MEDIUM
    )
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_by: Mapped["User"] = relationship()
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="incident", passive_deletes="all")
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(back_populates="incident", passive_deletes="all")


@event.listens_for(Incident, 'before_insert')
def initialize_timestamps(_mapper, _connection, target):
    # Includes trusted CLI creation; historical migration rows remain unknown/null.
    if target.created_at is None:
        target.created_at = utc_now()
    target.updated_at = target.created_at
