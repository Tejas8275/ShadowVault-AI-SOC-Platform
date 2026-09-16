"""Append within the case caller's transaction. Never touch evidence custody."""
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, func
from app.models import CaseHistoryEvent
from app.schemas.case_history import Changes, CaseHistoryPage

FIELDS=('title','description','status','severity')


def snapshot(record):
    return {field: getattr(record,field) for field in FIELDS}


def append(db, record, actor, *, before=None, source='api'):
    after=snapshot(record)
    changes={field:{'before':before[field] if before is not None else None,'after':value}
             for field,value in after.items() if before is None or before[field]!=value}
    try:
        changes=Changes.model_validate(changes).model_dump(mode='json',exclude_none=True)
        # Retain null 'before' for creation snapshots.
        for field in changes:
            changes[field].setdefault('before',None)
    except ValidationError:
        raise HTTPException(503,'Case save not confirmed; history values require review') from None
    db.add(CaseHistoryEvent(incident_id=record.id,revision=record.revision,
        event_type='case_created' if before is None else 'case_updated',schema_version=1,
        actor_type='user',actor_user_id=actor.id,actor_label=actor.display_name,
        system_actor=None,recorded_at=record.created_at if before is None else record.updated_at,
        changes=changes,source=source))
    db.flush()


def search(db, incident_id, actor_id, after_revision, limit):
    from app.services.incidents import require_incident
    require_incident(db,incident_id,actor_id)
    query=select(CaseHistoryEvent).where(CaseHistoryEvent.incident_id==incident_id)
    first=db.scalar(select(func.min(CaseHistoryEvent.revision)).where(CaseHistoryEvent.incident_id==incident_id))
    if after_revision is not None:
        query=query.where(CaseHistoryEvent.revision>after_revision)
    rows=db.scalars(query.order_by(CaseHistoryEvent.revision).limit(limit+1)).all()
    return CaseHistoryPage(items=rows[:limit],tracking_started=first is not None,
        tracking_started_revision=first,next_revision=rows[limit-1].revision if len(rows)>limit else None)
