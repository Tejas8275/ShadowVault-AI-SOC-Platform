"""Immutable approved file manifest for a specific agent and incident."""
from uuid import UUID
from sqlalchemy import CheckConstraint, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.common import RecordMixin


class CollectionJob(RecordMixin, Base):
    __tablename__ = "collection_jobs"
    __table_args__ = (
        UniqueConstraint("id", "incident_id", name="uq_collection_jobs_id_incident"),
        CheckConstraint("status IN ('open', 'complete', 'cancelled')", name="status"),
    )

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id", ondelete="RESTRICT"), index=True)
    agent_id: Mapped[UUID] = mapped_column(ForeignKey("agents.id", ondelete="RESTRICT"), index=True)
    requested_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    selected_files: Mapped[list[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="open")
