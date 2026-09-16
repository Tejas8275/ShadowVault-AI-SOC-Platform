"""Authorized, idempotent observations; no evidence reads or acquisition changes."""
import base64
import hashlib
import json
from datetime import timezone
from uuid import UUID, uuid4
from fastapi import HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import and_, func, or_, select
from app.models import Evidence, Incident, TimelineEvent
from app.schemas.timeline import TimelinePage, TimelineResponse
from app.services import custody
from app.services.evidence_query import authorized_query as evidence_scope, require_evidence, query_binding


def require_incident(db, incident_id, user_id):
    incident = db.get(Incident, incident_id, populate_existing=True)
    if incident is None or incident.created_by_id != user_id:
        raise HTTPException(404, 'Incident not found')
    return incident


def authorized_query(user_id):
    return select(TimelineEvent).join(Incident, Incident.id == TimelineEvent.incident_id).where(
        Incident.created_by_id == user_id,
        or_(TimelineEvent.evidence_id.is_(None), TimelineEvent.evidence_id.in_(evidence_scope(user_id).with_only_columns(Evidence.id))))


def details(db, event_id, user_id):
    event = db.scalar(authorized_query(user_id).where(TimelineEvent.id == event_id))
    if event is None:
        raise HTTPException(404, 'Timeline event not found')
    return TimelineResponse.model_validate(event)


def fingerprint(evidence_id, payload):
    # Versioned canonical payload preserves reported offset; changing it is a different submission.
    values = {'version': 1, 'evidence_id': str(evidence_id), **payload.model_dump(mode='json', exclude={'submission_id'})}
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def create(db, evidence_id, actor, payload):
    evidence = require_evidence(db, evidence_id, actor.id)
    digest = fingerprint(evidence_id, payload)
    existing = db.scalar(select(TimelineEvent).where(TimelineEvent.recorded_by_id == actor.id,
                                                     TimelineEvent.submission_id == payload.submission_id))
    if existing is not None:
        if existing.request_sha256 != digest:
            raise HTTPException(409, 'Submission ID already belongs to different content')
        return details(db, existing.id, actor.id), False
    operation_id = uuid4()
    custody.ensure_baseline(db, evidence, operation_id, reason='tracking_started_at_first_timeline_event')
    event = TimelineEvent(id=uuid4(), incident_id=evidence.incident_id, evidence_id=evidence.id,
        recorded_by_id=actor.id, recorded_by_label=actor.display_name, origin='investigator',
        occurred_at=payload.occurred_at.astimezone(timezone.utc), reported_time=payload.occurred_at.isoformat(), title=payload.title,
        description=payload.description, source=payload.source, source_locator=payload.source_locator,
        submission_id=payload.submission_id, request_sha256=digest)
    db.add(event)
    db.flush()
    custody.append_event(db, evidence, event_type='timeline_observation_added', actor_user=actor,
        operation_id=operation_id, details={'timeline_event_id': str(event.id), 'request_sha256': digest,
            'evidence_sha256': evidence.sha256, 'origin': 'investigator'})
    return TimelineResponse.model_validate(event), True


class Cursor(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: int = Field(default=1, ge=1, le=1)
    occurred_at: AwareDatetime
    id: UUID
    binding: str = Field(pattern=r'^[0-9a-f]{64}$')


def decode(value, binding):
    try:
        cursor = Cursor.model_validate_json(base64.b64decode(value, altchars=b'-_', validate=True))
        if cursor.binding != binding:
            raise ValueError()
        return cursor
    except (ValueError, TypeError):
        raise HTTPException(422, 'Invalid cursor or cursor does not match the current query') from None


def search(db, actor_id, filters):
    require_incident(db, filters.incident_id, actor_id)
    query = authorized_query(actor_id).where(TimelineEvent.incident_id == filters.incident_id)
    if filters.evidence_id:
        evidence = require_evidence(db, filters.evidence_id, actor_id)
        if evidence.incident_id != filters.incident_id:
            raise HTTPException(404, 'Evidence not found')
        query = query.where(TimelineEvent.evidence_id == filters.evidence_id)
    if filters.origin:
        query = query.where(TimelineEvent.origin == filters.origin)
    if filters.occurred_from:
        query = query.where(TimelineEvent.occurred_at >= filters.occurred_from)
    if filters.occurred_to:
        query = query.where(TimelineEvent.occurred_at <= filters.occurred_to)
    if filters.q:
        literal = filters.q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        query = query.where(or_(*(column.ilike(f'%{literal}%', escape='\\') for column in
                                 (TimelineEvent.title, TimelineEvent.description, TimelineEvent.source, TimelineEvent.source_locator))))
    total = db.scalar(select(func.count()).select_from(query.with_only_columns(TimelineEvent.id).subquery()))
    binding = query_binding({'timeline_version': 1, 'actor': str(actor_id),
        'filters': filters.model_dump(mode='json', exclude={'cursor', 'limit'})})
    if filters.cursor:
        cursor = decode(filters.cursor, binding)
        if filters.sort == 'oldest':
            query = query.where(or_(TimelineEvent.occurred_at > cursor.occurred_at,
                and_(TimelineEvent.occurred_at == cursor.occurred_at, TimelineEvent.id > cursor.id)))
        else:
            query = query.where(or_(TimelineEvent.occurred_at < cursor.occurred_at,
                and_(TimelineEvent.occurred_at == cursor.occurred_at, TimelineEvent.id < cursor.id)))
    order = (TimelineEvent.occurred_at, TimelineEvent.id) if filters.sort == 'oldest' else (TimelineEvent.occurred_at.desc(), TimelineEvent.id.desc())
    rows = db.scalars(query.order_by(*order).limit(filters.limit + 1)).all()
    page = rows[:filters.limit]
    cursor = None
    if len(rows) > filters.limit:
        cursor = base64.urlsafe_b64encode(Cursor(occurred_at=page[-1].occurred_at, id=page[-1].id, binding=binding).model_dump_json().encode()).decode()
    return TimelinePage(items=page, total=total, next_cursor=cursor)
