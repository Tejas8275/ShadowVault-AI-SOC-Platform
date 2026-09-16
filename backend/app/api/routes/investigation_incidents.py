"""Additive case management; legacy v1 placeholders remain compatible."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Query, HTTPException, Response, Request
from sqlalchemy.exc import SQLAlchemyError
from app.core.security import Database, Operator
from app.schemas.incident import IncidentCreate, IncidentUpdate, IncidentResponse, IncidentFilters, IncidentPage
from app.services import incidents
from app.services import case_history
from app.schemas.case_history import CaseHistoryPage
from app.schemas.incident import IncidentDetail
from app.services import case_intelligence
from app.services import case_report
from app.schemas.case_report import CaseReportDraft
from app.core.security import Credentials, require_operator
from app.schemas.ai_briefing import BriefingRequest, CaseBriefing
from app.services import ai_briefing

router = APIRouter(prefix='/api/v2/investigation/incidents', tags=['cases'])


@router.post('/{id}/ai-briefing', response_model=CaseBriefing)
async def briefing(id: UUID, payload: BriefingRequest, request: Request, response: Response,
                   db: Database, actor: Operator, credentials: Credentials):
    response.headers['Cache-Control'] = 'no-store'
    try:
        return await ai_briefing.generate(request, db, credentials, actor.id, id)
    except SQLAlchemyError:
        raise HTTPException(503, 'AI metadata unavailable; retry manually') from None


@router.get('/{id}/report-draft', response_model=CaseReportDraft)
def report_draft(id: UUID, request: Request, response: Response, db: Database, actor: Operator, credentials: Credentials):
    response.headers['Cache-Control'] = 'no-store'
    actor_id = actor.id
    try:
        draft = case_report.build(db, id, actor_id)
        current = require_operator(request, db, credentials)
        case_report.recheck_scope(db, draft, current.id)
        return draft
    except SQLAlchemyError:
        raise HTTPException(503, 'Case report unavailable; retry manually') from None
    finally:
        db.rollback()


@router.get('/{id}/history', response_model=CaseHistoryPage)
def history(id: UUID, response: Response, db: Database, actor: Operator,
            after_revision: Annotated[int | None, Query(ge=0)] = None,
            limit: Annotated[int, Query(ge=1, le=100)] = 50):
    response.headers['Cache-Control']='no-store'
    return case_history.search(db,id,actor.id,after_revision,limit)


@router.get('', response_model=IncidentPage)
def list_cases(db: Database, actor: Operator, filters: Annotated[IncidentFilters, Query()]):
    return incidents.search(db, actor.id, filters)


@router.get('/{id}', response_model=IncidentDetail, response_model_exclude_unset=True)
def detail(id: UUID, response: Response, db: Database, actor: Operator, include_intelligence: bool = False):
    response.headers['Cache-Control'] = 'no-store'
    record = incidents.require_incident(db, id, actor.id)
    result = IncidentDetail.model_validate(record)
    if include_intelligence:
        try:
            result.intelligence = case_intelligence.summarize(db, record, actor.id)
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(503, 'Case overview unavailable') from None
    return result


def write(db, operation):
    try:
        result = operation(); db.commit(); return result
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, 'Case save not confirmed; reload cases before trying again') from None
    except Exception:
        db.rollback(); raise


@router.post('', response_model=IncidentResponse, status_code=201)
def create(payload: IncidentCreate, db: Database, actor: Operator):
    return write(db, lambda: incidents.create(db, actor.id, payload))


@router.patch('/{id}', response_model=IncidentResponse)
def edit(id: UUID, payload: IncidentUpdate, db: Database, actor: Operator):
    return write(db, lambda: incidents.edit(db, id, actor.id, payload))
