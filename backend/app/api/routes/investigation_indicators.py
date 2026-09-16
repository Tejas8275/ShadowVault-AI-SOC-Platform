"""Additive indicator APIs. Original evidence and case state stay unchanged."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.core.security import Database, Operator
from app.schemas.indicator import IndicatorCreate, IndicatorResponse, IndicatorPage, Kind
from app.services import indicators
router=APIRouter(prefix='/api/v2/investigation',tags=['indicators'])

@router.post('/evidence/{evidence_id}/indicators',response_model=IndicatorResponse,status_code=201)
def create(evidence_id:UUID,payload:IndicatorCreate,response:Response,db:Database,actor:Operator):
    response.headers['Cache-Control']='no-store'
    try:
        result=indicators.create(db,evidence_id,actor,payload);db.commit();return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'Concurrent indicator submission; retry the same submission or reload corrections') from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503,'Indicator save not confirmed; retry the same submission') from None
    except Exception:
        db.rollback();raise

@router.get('/incidents/{incident_id}/indicators',response_model=IndicatorPage)
def search(incident_id:UUID,response:Response,db:Database,actor:Operator,
           evidence_id:UUID|None=None,kind:Kind|None=None,observation_id:UUID|None=None,
           value:Annotated[str|None,Query(min_length=1,max_length=255)]=None,
           cursor:Annotated[str|None,Query(max_length=1024)]=None,
           limit:Annotated[int,Query(ge=1,le=100)]=50):
    response.headers['Cache-Control']='no-store'
    try: return indicators.search(db,incident_id,actor.id,evidence_id,kind,value,cursor,limit,observation_id)
    except SQLAlchemyError:
        db.rollback();raise HTTPException(503,'Indicators unavailable') from None
