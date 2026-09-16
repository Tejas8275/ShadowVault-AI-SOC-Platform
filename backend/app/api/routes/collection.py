"""Operator control plane and agent-only ingestion. Existing Phase 1 routes stay stable."""
import asyncio
import secrets
from datetime import timedelta
from typing import Annotated
from uuid import UUID, uuid4
from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.requests import ClientDisconnect
from app.core.security import Database, Device, Operator, active_agent, token_digest
from app.models import Agent, CollectionJob, Evidence, Incident
from app.models.common import utc_now
from app.schemas.collection import AgentRegistration, RegisteredAgent, JobRequest, JobResponse, UploadMetadata, EvidenceReceipt
from app.services.collection import agent_job, operator_job, manifest_item, job_response, receipt_for, check_duplicate, make_evidence
from app.services.storage import EvidenceStore

router = APIRouter(tags=["collection"])


@router.post("/agents", response_model=RegisteredAgent, status_code=201)
def register_agent(payload: AgentRegistration, request: Request, response: Response, db: Database, operator: Operator):
    token = "sv_agent_" + secrets.token_urlsafe(32)
    agent = Agent(name=payload.name, platform=payload.platform, collector_version=payload.collector_version,
                  registered_by_id=operator.id, token_sha256=token_digest(token),
                  token_expires_at=utc_now() + timedelta(hours=request.app.state.settings.agent_token_hours))
    db.add(agent)
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return RegisteredAgent(id=agent.id, name=agent.name, token=token, token_expires_at=agent.token_expires_at)


@router.delete("/agents/{agent_id}", status_code=204)
def revoke_agent(agent_id: UUID, db: Database, operator: Operator):
    agent = db.get(Agent, agent_id)
    if agent is None or agent.registered_by_id != operator.id:
        raise HTTPException(404, "Agent not found")
    agent.is_active = False
    db.commit()


@router.post("/collection-jobs", response_model=JobResponse, status_code=201)
def create_job(payload: JobRequest, request: Request, db: Database, operator: Operator):
    incident = db.get(Incident, payload.incident_id)
    agent = db.get(Agent, payload.agent_id)
    if incident is None or incident.created_by_id != operator.id:
        raise HTTPException(404, "Incident not found")
    if agent is None or agent.registered_by_id != operator.id:
        raise HTTPException(404, "Agent not found")
    if not agent.is_active or agent.token_expires_at <= utc_now():
        raise HTTPException(409, "Agent is inactive or expired")
    settings = request.app.state.settings
    if any(item.max_bytes > settings.max_upload_bytes for item in payload.files) or sum(item.max_bytes for item in payload.files) > settings.max_job_bytes:
        raise HTTPException(422, "Selected file limits exceed server policy")
    job = CollectionJob(incident_id=incident.id, agent_id=agent.id, requested_by_id=operator.id,
                        selected_files=[{"id": str(uuid4()), **item.model_dump()} for item in payload.files])
    db.add(job)
    db.commit()
    return job_response(db, job)


@router.get("/collection-jobs/{job_id}", response_model=JobResponse)
def read_job(job_id: UUID, db: Database, operator: Operator):
    return job_response(db, operator_job(db, job_id, operator.id))


@router.post("/collection-jobs/{job_id}/cancel", status_code=204)
def cancel_job(job_id: UUID, db: Database, operator: Operator):
    job = operator_job(db, job_id, operator.id)
    job.status = "cancelled"
    db.commit()


@router.get("/collection-jobs/{job_id}/evidence", response_model=list[EvidenceReceipt])
def list_job_evidence(job_id: UUID, db: Database, operator: Operator):
    operator_job(db, job_id, operator.id)
    return db.scalars(select(Evidence).where(Evidence.collection_job_id == job_id).order_by(Evidence.created_at)).all()


@router.get("/agents/jobs/{job_id}", response_model=JobResponse)
def agent_manifest(job_id: UUID, db: Database, agent: Device):
    return job_response(db, agent_job(db, job_id, agent))


@router.put("/agents/jobs/{job_id}/files/{item_id}", response_model=EvidenceReceipt, status_code=201,
            responses={200: {"model": EvidenceReceipt, "description": "Identical retry; original receipt"}},
            openapi_extra={"requestBody": {"required": True, "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
async def upload_file(job_id: UUID, item_id: UUID, request: Request, response: Response,
                      db: Database, agent: Device,
                      sha256: Annotated[str, Header(alias="X-Evidence-SHA256", max_length=64)],
                      size_bytes: Annotated[int, Header(alias="X-Evidence-Size", ge=0)],
                      collected_at: Annotated[str, Header(alias="X-Collected-At", max_length=64)]):
    try:
        metadata = UploadMetadata(sha256=sha256, size_bytes=size_bytes, collected_at=collected_at)
    except ValidationError:
        raise HTTPException(422, "Invalid digest, size or timezone-aware collection timestamp") from None
    if request.headers.get("content-type", "").lower() != "application/octet-stream":
        raise HTTPException(415, "Use application/octet-stream")
    if request.headers.get("content-encoding", "identity").lower() != "identity":
        raise HTTPException(415, "Encoded uploads are not supported")
    job = agent_job(db, job_id, agent)
    item = manifest_item(job, item_id)
    settings = request.app.state.settings
    limit = min(item["max_bytes"], settings.max_upload_bytes)
    if size_bytes > limit:
        raise HTTPException(413, "Upload exceeds the approved size")
    if request.app.state.upload_slots.locked():
        raise HTTPException(429, "Upload capacity reached; retry later", headers={"Retry-After": "5"})
    digest = agent.token_sha256
    # Release the read transaction while receiving bytes, then recheck authorization.
    db.rollback()
    store = EvidenceStore(settings.evidence_dir)
    temporary = final = None
    committed = False
    try:
        async with asyncio.timeout(settings.upload_timeout_seconds):
            async with request.app.state.upload_slots:
                temporary = await store.receive(request, metadata, limit, settings.upload_timeout_seconds)
        agent = active_agent(db, digest)
        job = agent_job(db, job_id, agent)
        item = manifest_item(job, item_id)
        existing = receipt_for(db, job_id, item_id)
        if existing is not None:
            response.status_code = 200
            return check_duplicate(existing, sha256, size_bytes)
        final = store.promote(temporary)
        evidence = make_evidence(job, item, metadata, final.name)
        db.add(evidence)
        try:
            db.commit()
        except IntegrityError:
            # A simultaneous retry may win the unique (job, item) constraint.
            db.rollback()
            existing = receipt_for(db, job_id, item_id)
            if existing is None:
                raise
            response.status_code = 200
            return check_duplicate(existing, sha256, size_bytes)
        committed = True
        return evidence
    except TimeoutError:
        raise HTTPException(408, "Upload timed out; retry the same selected file") from None
    except ClientDisconnect:
        raise HTTPException(400, "Upload interrupted") from None
    except (OSError, SQLAlchemyError):
        db.rollback()
        raise HTTPException(503, "Evidence could not be stored; retry the same selected file") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        if final is not None and not committed:
            final.unlink(missing_ok=True)
