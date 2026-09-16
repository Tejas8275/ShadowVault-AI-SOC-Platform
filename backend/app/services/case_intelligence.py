"""Read-only case aggregates; no evidence reads, analysis, or history writes."""
from sqlalchemy import select, func
from app.models import Evidence, TimelineEvent, CaseHistoryEvent, CustodyEvent
from app.services.evidence_query import authorized_query as evidence_scope
from app.services.timeline import authorized_query as timeline_scope
from app.schemas.incident import CaseIntelligence


def summarize(db, record, actor_id):
    evidence = evidence_scope(actor_id).where(Evidence.incident_id == record.id).subquery()
    timeline = timeline_scope(actor_id).where(TimelineEvent.incident_id == record.id).subquery()
    history = select(CaseHistoryEvent).where(CaseHistoryEvent.incident_id == record.id).subquery()
    custody = select(CustodyEvent.recorded_at).where(
        CustodyEvent.evidence_id.in_(select(evidence.c.id))).subquery()
    # One aggregate SELECT; all evidence-linked values inherit the stricter
    # case-owner AND collection-requester visibility rule, including custody.
    values = db.execute(select(
        select(func.count()).select_from(evidence).scalar_subquery(),
        select(func.count()).select_from(timeline).scalar_subquery(),
        select(func.count()).select_from(history).scalar_subquery(),
        select(func.min(history.c.revision)).scalar_subquery(),
        select(func.max(evidence.c.created_at)).scalar_subquery(),
        select(func.max(timeline.c.created_at)).scalar_subquery(),
        select(func.max(history.c.recorded_at)).scalar_subquery(),
        select(func.max(custody.c.recorded_at)).scalar_subquery(),
    )).one()
    stamps = [record.created_at, record.updated_at, *values[4:]]
    return CaseIntelligence(evidence_count=values[0], timeline_count=values[1],
        history_revision_count=values[2], history_started_revision=values[3],
        latest_activity_at=max(stamp for stamp in stamps if stamp is not None))
