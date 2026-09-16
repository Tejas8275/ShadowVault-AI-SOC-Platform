"""Owner-scoped cases. Status is descriptive and never changes collection policy."""
from fastapi import HTTPException
from sqlalchemy import select, update, func, and_, or_
from app.models import Incident
from app.models.incident import IncidentStatus
from app.models.common import utc_now
from app.schemas.incident import IncidentPage, IncidentResponse
from app.services.evidence_query import query_binding, encode_cursor, decode_cursor
from app.services import case_history
from app.models import User

TRANSITIONS = {'open': {'open', 'investigating'}, 'investigating': {'investigating', 'closed'},
               'closed': {'closed', 'investigating'}}


def require_incident(db, id, actor_id):
    record = db.scalar(select(Incident).where(Incident.id == id, Incident.created_by_id == actor_id)
                       .execution_options(populate_existing=True))
    if record is None: raise HTTPException(404, 'Case not found')
    return record


def search(db, actor_id, filters):
    query = select(Incident).where(Incident.created_by_id == actor_id)
    for field in ('status', 'severity'):
        if getattr(filters, field) is not None: query = query.where(getattr(Incident, field) == getattr(filters, field))
    if filters.q:
        value = filters.q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        query = query.where(or_(Incident.title.ilike(f'%{value}%', escape='\\'), Incident.description.ilike(f'%{value}%', escape='\\')))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    binding = query_binding({'case_version': 1, 'actor': str(actor_id),
        'filters': filters.model_dump(mode='json', exclude={'cursor', 'limit'})})
    if filters.cursor:
        cursor = decode_cursor(filters.cursor, binding)
        query = query.where(or_(Incident.created_at < cursor.created_at,
            and_(Incident.created_at == cursor.created_at, Incident.id < cursor.id)))
    rows = db.scalars(query.order_by(Incident.created_at.desc(), Incident.id.desc()).limit(filters.limit + 1)).all()
    page = rows[:filters.limit]
    return IncidentPage(items=page, total=total, next_cursor=encode_cursor(page[-1], binding) if len(rows) > filters.limit else None)


def create(db, actor_id, payload, *, source='api'):
    record = Incident(**payload.model_dump(), created_by_id=actor_id, status=IncidentStatus.OPEN)
    db.add(record); db.flush()
    case_history.append(db,record,db.get(User,actor_id),source=source)
    return IncidentResponse.model_validate(record)


def edit(db, id, actor_id, payload):
    record = require_incident(db, id, actor_id)
    if record.revision != payload.expected_revision: raise HTTPException(409, 'Case changed; reload before saving')
    if payload.status.value not in TRANSITIONS[record.status.value]:
        raise HTTPException(422, 'Invalid case status transition')
    before=case_history.snapshot(record)
    changed = db.execute(update(Incident).where(Incident.id == id, Incident.created_by_id == actor_id,
        Incident.revision == payload.expected_revision).values(**payload.model_dump(exclude={'expected_revision'}, exclude_unset=True),
        revision=payload.expected_revision + 1, updated_at=utc_now()).execution_options(synchronize_session=False))
    if changed.rowcount != 1: raise HTTPException(409, 'Case changed; reload before saving')
    record=require_incident(db, id, actor_id)
    case_history.append(db,record,db.get(User,actor_id),before=before)
    return IncidentResponse.model_validate(record)
