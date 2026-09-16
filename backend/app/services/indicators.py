"""Case/evidence-authorized observation registration, without custody mutation."""
from fastapi import HTTPException
from sqlalchemy import select, and_, or_
from app.models import Evidence, IndicatorObservation
from app.schemas.indicator import IndicatorResponse, IndicatorListItem, IndicatorPage, normalize
from app.services import evidence_query, incidents


def scoped(actor_id):
    return select(IndicatorObservation).where(IndicatorObservation.evidence_id.in_(
        evidence_query.authorized_query(actor_id).with_only_columns(Evidence.id)))


def create(db,evidence_id,actor,payload):
    evidence=evidence_query.require_evidence(db,evidence_id,actor.id)
    digest=evidence_query.query_binding({'evidence_id':str(evidence_id),**payload.model_dump(mode='json',exclude={'submission_id'})})
    old=db.scalar(select(IndicatorObservation).where(IndicatorObservation.created_by_id==actor.id,IndicatorObservation.submission_id==payload.submission_id))
    if old:
        if old.evidence_id!=evidence_id or old.request_sha256!=digest: raise HTTPException(409,'Submission ID conflicts with an existing observation')
        return IndicatorResponse.model_validate(old)
    if payload.supersedes_id:
        previous=db.scalar(scoped(actor.id).where(IndicatorObservation.id==payload.supersedes_id,IndicatorObservation.evidence_id==evidence_id))
        if previous is None: raise HTTPException(404,'Indicator observation not found')
        if db.scalar(select(IndicatorObservation.id).where(IndicatorObservation.supersedes_id==previous.id)):
            raise HTTPException(409,'Observation already has a correction; reload indicators')
    raw=payload.raw_value
    locator=payload.source_locator
    if payload.source_kind!='manual':
        locator='sha256' if payload.source_kind=='evidence_sha256' else 'filename'
        raw=getattr(evidence,locator)
    try: normalized=normalize(payload.kind,raw)
    except ValueError: raise HTTPException(422,'Source metadata cannot be represented as this indicator kind') from None
    record=IndicatorObservation(incident_id=evidence.incident_id,evidence_id=evidence.id,kind=payload.kind,
        raw_value=raw,normalized_value=normalized,source_kind=payload.source_kind,source_locator=locator,
        created_by_id=actor.id,actor_label=actor.display_name,submission_id=payload.submission_id,
        request_sha256=digest,supersedes_id=payload.supersedes_id)
    db.add(record);db.flush()
    return IndicatorResponse.model_validate(record)


def search(db,incident_id,actor_id,evidence_id=None,kind=None,value=None,cursor=None,limit=50,observation_id=None):
    incidents.require_incident(db,incident_id,actor_id)
    if evidence_id:
        evidence=evidence_query.require_evidence(db,evidence_id,actor_id)
        if evidence.incident_id!=incident_id: raise HTTPException(404,'Evidence not found')
    if value is not None:
        if kind is None: raise HTTPException(422,'Exact value filtering requires an indicator kind')
        try: value=normalize(kind,value)
        except ValueError: raise HTTPException(422,'Invalid indicator filter') from None
    binding_values={'indicators':str(incident_id),'actor':str(actor_id),'evidence':str(evidence_id),'kind':kind,'value':value}
    if observation_id is not None: binding_values['observation_id']=str(observation_id)
    binding=evidence_query.query_binding(binding_values)
    query=scoped(actor_id).where(IndicatorObservation.incident_id==incident_id)
    if observation_id: query=query.where(IndicatorObservation.id==observation_id)
    if evidence_id: query=query.where(IndicatorObservation.evidence_id==evidence_id)
    if kind: query=query.where(IndicatorObservation.kind==kind)
    if value is not None: query=query.where(IndicatorObservation.normalized_value==value)
    if cursor:
        position=evidence_query.decode_cursor(cursor,binding)
        query=query.where(or_(IndicatorObservation.created_at>position.created_at,and_(IndicatorObservation.created_at==position.created_at,IndicatorObservation.id>position.id)))
    rows=db.scalars(query.order_by(IndicatorObservation.created_at,IndicatorObservation.id).limit(limit+1)).all()
    page=rows[:limit]
    # Resolve successors against authorized source rows, independently of page and value filters.
    originals={row.id:row for row in page}
    successors={}
    if originals:
        for successor in db.scalars(scoped(actor_id).where(IndicatorObservation.supersedes_id.in_(originals),IndicatorObservation.incident_id==incident_id)):
            original=originals[successor.supersedes_id]
            if successor.evidence_id==original.evidence_id:
                successors[original.id]=successor.id
    items=[IndicatorListItem.model_validate(row).model_copy(update={'superseded_by_id':successors.get(row.id)}) for row in page]
    return IndicatorPage(items=items,next_cursor=evidence_query.encode_cursor(rows[limit-1],binding) if len(rows)>limit else None)
