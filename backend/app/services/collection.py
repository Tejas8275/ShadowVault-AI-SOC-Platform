from pathlib import PureWindowsPath
from datetime import timezone
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models import Agent, CollectionJob, Evidence, Incident
from app.models.common import utc_now
from app.schemas.collection import JobResponse


def operator_job(db: Session, job_id: UUID, user_id: UUID) -> CollectionJob:
    job = db.get(CollectionJob, job_id, populate_existing=True)
    if job is None or job.requested_by_id != user_id:
        raise HTTPException(404, "Collection job not found")
    incident = db.get(Incident, job.incident_id, populate_existing=True)
    if incident is None or incident.created_by_id != user_id:
        raise HTTPException(404, "Collection job not found")
    return job


def agent_job(db: Session, job_id: UUID, agent: Agent) -> CollectionJob:
    job = operator_job(db, job_id, agent.registered_by_id)
    if job.agent_id != agent.id:
        raise HTTPException(404, "Collection job not found")
    if job.status == "cancelled":
        raise HTTPException(409, "Collection job is cancelled")
    return job


def manifest_item(job: CollectionJob, item_id: UUID) -> dict:
    item = next((item for item in job.selected_files if item["id"] == str(item_id)), None)
    if item is None:
        raise HTTPException(404, "Selected file not found")
    return item


def receipt_for(db: Session, job_id: UUID, item_id: UUID) -> Evidence | None:
    return db.scalar(select(Evidence).where(Evidence.collection_job_id == job_id,
                                          Evidence.collection_item_id == item_id))


def check_duplicate(existing: Evidence, digest: str, size: int) -> Evidence:
    if existing.sha256 != digest or existing.size_bytes != size:
        raise HTTPException(409, "This selected file already has different evidence; create a new job")
    return existing


def job_response(db: Session, job: CollectionJob) -> JobResponse:
    count = db.scalar(select(func.count()).select_from(Evidence).where(Evidence.collection_job_id == job.id))
    status = "complete" if job.status != "cancelled" and count == len(job.selected_files) else job.status
    return JobResponse(id=job.id, incident_id=job.incident_id, agent_id=job.agent_id,
                       status=status, files=job.selected_files, completed_files=count)


def make_evidence(job, item, metadata, storage_key):
    return Evidence(incident_id=job.incident_id, collected_by_id=job.requested_by_id,
                    collection_job_id=job.id, collection_item_id=UUID(item["id"]),
                    filename=PureWindowsPath(item["source_path"]).name, source_path=item["source_path"],
                    size_bytes=metadata.size_bytes, sha256=metadata.sha256, storage_key=storage_key,
                    collected_at=metadata.collected_at.astimezone(timezone.utc),
                    verified_at=utc_now(), verification_status="verified")
