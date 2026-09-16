"""Incident-authorized metadata queries. No storage reads or implicit custody writes."""
import base64
import hashlib
import json
from uuid import UUID
from fastapi import HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import and_, func, or_, select
from app.models import CollectionJob, Evidence, EvidenceIntegrityCheck, EvidenceNote, EvidenceTag, Incident
from app.schemas.investigation import EvidenceDetails, EvidenceSummary, SearchPage


def authorized_query(user_id):
    return select(Evidence).join(Incident, Incident.id == Evidence.incident_id).where(
        Incident.created_by_id == user_id,
        or_(Evidence.collection_job_id.is_(None),
            select(CollectionJob.id).where(CollectionJob.id == Evidence.collection_job_id,
                                            CollectionJob.requested_by_id == user_id).exists()),
    )


def require_evidence(db, evidence_id, user_id):
    evidence = db.scalar(authorized_query(user_id).where(Evidence.id == evidence_id).execution_options(populate_existing=True))
    if evidence is None:
        raise HTTPException(404, "Evidence not found")
    return evidence


def latest_check_column(column):
    return (select(column).where(EvidenceIntegrityCheck.evidence_id == Evidence.id,
                                 EvidenceIntegrityCheck.status.in_(["completed", "failed"]))
            .order_by(EvidenceIntegrityCheck.created_at.desc(), EvidenceIntegrityCheck.id.desc())
            .limit(1).correlate(Evidence).scalar_subquery())


class Cursor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(default=1, ge=1, le=1)
    created_at: AwareDatetime
    id: UUID
    binding: str = Field(pattern=r"^[0-9a-f]{64}$")


def encode_cursor(record, binding):
    value = Cursor(created_at=record.created_at, id=record.id, binding=binding)
    return base64.urlsafe_b64encode(value.model_dump_json().encode()).decode()


def decode_cursor(value, binding):
    try:
        raw = base64.b64decode(value, altchars=b'-_', validate=True)
        cursor = Cursor.model_validate_json(raw)
        if cursor.binding != binding:
            raise ValueError()
        return cursor
    except (ValueError, TypeError):
        raise HTTPException(422, "Invalid cursor or cursor does not match the current query") from None


def query_binding(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def summaries(db, records):
    if not records:
        return []
    ids = [record.id for record in records]
    tags = {id: [] for id in ids}
    for evidence_id, tag in db.execute(select(EvidenceTag.evidence_id, EvidenceTag.tag)
                                       .where(EvidenceTag.evidence_id.in_(ids)).order_by(EvidenceTag.tag)):
        tags[evidence_id].append(tag)
    checks = dict((id, (result, time)) for id, result, time in db.execute(
        select(Evidence.id, latest_check_column(EvidenceIntegrityCheck.result),
               latest_check_column(EvidenceIntegrityCheck.completed_at)).where(Evidence.id.in_(ids))))
    output = []
    for record in records:
        summary = EvidenceSummary.model_validate(record)
        result, time = checks[record.id]
        output.append(summary.model_copy(update={"tags": tags[record.id], "integrity_result": result or "not_checked",
                                                "integrity_checked_at": time, "custody_started": record.custody_sequence > 0}))
    return output


def details(db, evidence_id, user_id):
    record = require_evidence(db, evidence_id, user_id)
    summary = summaries(db, [record])[0]
    job = db.get(CollectionJob, record.collection_job_id) if record.collection_job_id else None
    values = summary.model_dump()
    # Summary validation aliases only apply to ORM reads, not this already-safe DTO.
    values['verification_status'] = values.pop('initial_verification_status')
    values['verified_at'] = values.pop('initial_verified_at')
    return EvidenceDetails(**values, collected_by_user_id=record.collected_by_id,
                           requested_by_user_id=job.requested_by_id if job else None,
                           agent_id=job.agent_id if job else None, custody_sequence=record.custody_sequence,
                           custody_head_hash=record.custody_head_hash,
                           note_count=db.scalar(select(func.count()).select_from(EvidenceNote).where(EvidenceNote.evidence_id == record.id)))


def search(db, user_id, filters):
    query = authorized_query(user_id)
    for column, value in [(Evidence.incident_id, filters.incident_id),
                          (Evidence.collection_job_id, filters.collection_job_id),
                          (Evidence.review_state, filters.review_state),
                          (Evidence.verification_status, filters.verification_status)]:
        if value is not None:
            query = query.where(column == value)
    if filters.agent_id:
        query = query.where(select(CollectionJob.id).where(CollectionJob.id == Evidence.collection_job_id,
                                                          CollectionJob.agent_id == filters.agent_id).exists())
    if filters.sha256:
        query = query.where(Evidence.sha256 == filters.sha256.lower())
    if filters.q:
        value = filters.q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        query = query.where(or_(*(column.ilike(f'%{value}%', escape='\\') for column in
                                 (Evidence.filename, Evidence.display_title, Evidence.source_path))))
    for tag in filters.tags:
        query = query.where(select(EvidenceTag.evidence_id).where(EvidenceTag.evidence_id == Evidence.id,
                                                                 EvidenceTag.tag == tag).exists())
    for column, low, high in [(Evidence.created_at, filters.created_from, filters.created_to),
                              (Evidence.collected_at, filters.collected_from, filters.collected_to),
                              (Evidence.size_bytes, filters.min_size, filters.max_size)]:
        if low is not None:
            query = query.where(column >= low)
        if high is not None:
            query = query.where(column <= high)
    if filters.integrity_result:
        query = query.where(func.coalesce(latest_check_column(EvidenceIntegrityCheck.result), 'not_checked') == filters.integrity_result)
    total = db.scalar(select(func.count()).select_from(query.with_only_columns(Evidence.id).subquery()))
    binding = query_binding({'user_id': str(user_id), 'filters': filters.model_dump(mode='json', exclude={'cursor', 'limit'})})
    if filters.cursor:
        cursor = decode_cursor(filters.cursor, binding)
        if filters.sort == 'newest':
            query = query.where(or_(Evidence.created_at < cursor.created_at,
                                   and_(Evidence.created_at == cursor.created_at, Evidence.id < cursor.id)))
        else:
            query = query.where(or_(Evidence.created_at > cursor.created_at,
                                   and_(Evidence.created_at == cursor.created_at, Evidence.id > cursor.id)))
    ordering = (Evidence.created_at.desc(), Evidence.id.desc()) if filters.sort == 'newest' else (Evidence.created_at.asc(), Evidence.id.asc())
    records = db.scalars(query.order_by(*ordering).limit(filters.limit + 1)).all()
    page = records[:filters.limit]
    return SearchPage(items=summaries(db, page), total=total,
                      next_cursor=encode_cursor(page[-1], binding) if len(records) > filters.limit else None)
