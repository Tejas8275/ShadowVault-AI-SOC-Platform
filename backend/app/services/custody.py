"""Custody appends participate in the caller's transaction; never commit here."""
import hmac
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select, update
from app.core.custody_hash import hash_event
from app.models import CustodyEvent, Evidence
from app.models.common import utc_now


def append_event(db, evidence, *, event_type, details, operation_id, actor_user=None, system_actor=None):
    if (actor_user is None) == (system_actor is None):
        raise ValueError("Supply exactly one authenticated user or system actor")
    previous_sequence, previous_hash = evidence.custody_sequence, evidence.custody_head_hash
    event = CustodyEvent(id=uuid4(), evidence_id=evidence.id, sequence=previous_sequence + 1, schema_version=1,
                         event_type=event_type, actor_type='user' if actor_user else 'system',
                         actor_user_id=actor_user.id if actor_user else None, actor_agent_id=None,
                         system_actor=system_actor, actor_label=actor_user.display_name if actor_user else system_actor,
                         recorded_at=utc_now(), source_at=None, operation_id=operation_id,
                         details=details, previous_hash=previous_hash)
    event.event_hash = hash_event(event)
    changed = db.execute(update(Evidence).where(Evidence.id == evidence.id,
                                                Evidence.custody_sequence == previous_sequence,
                                                Evidence.custody_head_hash == previous_hash)
                         .values(custody_sequence=event.sequence, custody_head_hash=event.event_hash)
                         .execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise HTTPException(409, "Custody changed concurrently; reload and retry")
    db.add(event)
    db.flush()
    db.refresh(evidence)
    return event


def ensure_baseline(db, evidence, operation_id, *, reason='tracking_started_at_first_annotation'):
    if evidence.custody_sequence == 0:
        append_event(db, evidence, event_type='baseline_registered', operation_id=operation_id,
                     system_actor='investigation-service', details={
                         'reason': reason,
                         'initial_verification_status': evidence.verification_status,
                         'sha256': evidence.sha256, 'size_bytes': evidence.size_bytes,
                         'incident_id': str(evidence.incident_id),
                     })


def verify_chain(db, evidence_id):
    """Read-only verification against the stored head, not an external trust anchor."""
    evidence = db.get(Evidence, evidence_id, populate_existing=True)
    if evidence is None:
        raise ValueError("Evidence does not exist")
    head_sequence, head_hash = evidence.custody_sequence, evidence.custody_head_hash
    previous = None
    sequence = 0
    events = db.scalars(select(CustodyEvent).where(CustodyEvent.evidence_id == evidence_id,
                                                  CustodyEvent.sequence <= head_sequence)
                        .order_by(CustodyEvent.sequence).execution_options(populate_existing=True, yield_per=100))
    for event in events:
        sequence += 1
        if (event.sequence != sequence or event.previous_hash != previous or event.schema_version != 1
            or not hmac.compare_digest(event.event_hash, hash_event(event))):
            return False
        previous = event.event_hash
    return sequence == head_sequence and previous == head_hash
