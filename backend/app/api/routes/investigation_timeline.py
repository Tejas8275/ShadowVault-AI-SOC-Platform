"""Additive timeline APIs; legacy v1 placeholders remain unchanged."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.core.security import Database, Operator
from app.schemas.timeline import TimelineCreate, TimelineFilters, TimelinePage, TimelineResponse
from app.services import timeline

router = APIRouter(prefix='/api/v2/investigation', tags=['investigation timeline'])


@router.post('/evidence/{evidence_id}/timeline-events', response_model=TimelineResponse, status_code=201,
             responses={200: {'model': TimelineResponse, 'description': 'Identical submission retry'}})
def create_observation(evidence_id: UUID, payload: TimelineCreate, response: Response, db: Database, actor: Operator):
    try:
        result, created = timeline.create(db, evidence_id, actor, payload)
        db.commit()
        if not created:
            response.status_code = 200
        return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Concurrent submission; retry the same submission ID and content') from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, 'Submission not confirmed; retry only with the same submission ID and content') from None
    except Exception:
        db.rollback()
        raise


@router.get('/timeline-events', response_model=TimelinePage)
def search_observations(db: Database, actor: Operator, filters: Annotated[TimelineFilters, Query()]):
    return timeline.search(db, actor.id, filters)


@router.get('/timeline-events/{event_id}', response_model=TimelineResponse)
def observation_details(event_id: UUID, db: Database, actor: Operator):
    return timeline.details(db, event_id, actor.id)
