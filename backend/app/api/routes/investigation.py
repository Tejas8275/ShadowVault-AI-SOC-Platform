"""Operator-only investigation metadata APIs; acquisition remains on v1."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import SQLAlchemyError
from app.core.security import Database, Operator
from app.models import CustodyEvent, EvidenceNote
from app.schemas.investigation import (AnnotationPatch, CustodyPage, EvidenceDetails, EvidenceFilters,
                                      NoteCreate, NoteReceipt, NotesPage, SearchPage)
from app.services import evidence_metadata, evidence_query

router = APIRouter(prefix='/api/v2/investigation', tags=['investigation'])


@router.get('/evidence', response_model=SearchPage)
def search_evidence(db: Database, actor: Operator, filters: Annotated[EvidenceFilters, Query()]):
    return evidence_query.search(db, actor.id, filters)


@router.get('/evidence/{evidence_id}', response_model=EvidenceDetails)
def evidence_details(evidence_id: UUID, db: Database, actor: Operator):
    return evidence_query.details(db, evidence_id, actor.id)


@router.patch('/evidence/{evidence_id}/annotations', response_model=EvidenceDetails)
def annotate(evidence_id: UUID, payload: AnnotationPatch, db: Database, actor: Operator):
    try:
        evidence_metadata.annotate(db, evidence_id, actor, payload)
        result = evidence_query.details(db, evidence_id, actor.id)
        db.commit()
        return result
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, 'Unable to save annotation; reload before retrying') from None
    except Exception:
        db.rollback()
        raise


@router.post('/evidence/{evidence_id}/notes', response_model=NoteReceipt, status_code=201)
def add_note(evidence_id: UUID, payload: NoteCreate, db: Database, actor: Operator):
    try:
        note, revision = evidence_metadata.add_note(db, evidence_id, actor, payload)
        result = NoteReceipt(note=note, metadata_revision=revision)
        db.commit()
        return result
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, 'Unable to save note; reload before retrying') from None
    except Exception:
        db.rollback()
        raise


@router.get('/evidence/{evidence_id}/notes', response_model=NotesPage)
def notes(evidence_id: UUID, db: Database, actor: Operator,
          limit: Annotated[int, Query(ge=1, le=100)] = 50,
          cursor: Annotated[str | None, Query(max_length=1024)] = None):
    evidence_query.require_evidence(db, evidence_id, actor.id)
    binding = evidence_query.query_binding({'user': str(actor.id), 'notes': str(evidence_id)})
    query = select(EvidenceNote).where(EvidenceNote.evidence_id == evidence_id)
    if cursor:
        position = evidence_query.decode_cursor(cursor, binding)
        query = query.where(or_(EvidenceNote.created_at > position.created_at,
                              and_(EvidenceNote.created_at == position.created_at, EvidenceNote.id > position.id)))
    records = db.scalars(query.order_by(EvidenceNote.created_at, EvidenceNote.id).limit(limit + 1)).all()
    page = records[:limit]
    return NotesPage(items=page, next_cursor=evidence_query.encode_cursor(page[-1], binding) if len(records) > limit else None)


@router.get('/evidence/{evidence_id}/custody', response_model=CustodyPage)
def custody_history(evidence_id: UUID, db: Database, actor: Operator,
                    after_sequence: Annotated[int, Query(ge=0)] = 0,
                    limit: Annotated[int, Query(ge=1, le=100)] = 50):
    evidence = evidence_query.require_evidence(db, evidence_id, actor.id)
    records = db.scalars(select(CustodyEvent).where(CustodyEvent.evidence_id == evidence_id,
                                                  CustodyEvent.sequence > after_sequence,
                                                  CustodyEvent.sequence <= evidence.custody_sequence)
                         .order_by(CustodyEvent.sequence).limit(limit + 1)).all()
    return CustodyPage(items=records[:limit], tracking_started=evidence.custody_sequence > 0,
                      head_sequence=evidence.custody_sequence, head_hash=evidence.custody_head_hash,
                      next_sequence=records[limit - 1].sequence if len(records) > limit else None)
