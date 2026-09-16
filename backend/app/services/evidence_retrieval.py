"""Explicit retrieval preparation; original facts and integrity-check rows stay unchanged."""
from uuid import uuid4
from fastapi import HTTPException
from app.core.security import require_operator
from app.services import custody
from app.services.evidence_query import require_evidence
from app.services.evidence_reader import prepare_copy


def prepare(db, request, credentials, actor, evidence_id):
    evidence = require_evidence(db, evidence_id, actor.id)
    identity = (evidence.storage_key, evidence.size_bytes, evidence.sha256)
    db.rollback()  # Do not hold a database transaction while copying bytes.
    copy = prepare_copy(request.app.state.settings, *identity)
    try:
        actor = require_operator(request, db, credentials)
        evidence = require_evidence(db, evidence_id, actor.id)
        if (evidence.storage_key, evidence.size_bytes, evidence.sha256) != identity:
            raise HTTPException(409, 'Evidence changed during preparation')
        operation = uuid4()
        custody.ensure_baseline(db, evidence, operation, reason='tracking_started_at_first_retrieval')
        custody.append_event(db, evidence, event_type='evidence_retrieval_prepared', operation_id=operation,
            actor_user=actor, details={'expected_sha256': identity[2], 'observed_sha256': identity[2],
                'expected_size_bytes': identity[1], 'observed_size_bytes': identity[1],
                'meaning': 'Verified copy prepared; delivery and local saving are not confirmed'})
        db.commit()
        return copy, identity[1]
    except BaseException:
        copy.close()
        db.rollback()
        raise
