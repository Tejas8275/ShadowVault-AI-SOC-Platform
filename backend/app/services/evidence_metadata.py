"""Optimistic revisions and atomic metadata/custody writes. No acquisition edits."""
import hashlib
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import delete, select, update
from app.models import Evidence, EvidenceNote, EvidenceTag
from app.services import custody
from app.services.evidence_query import require_evidence


def claim_revision(db, evidence, expected_revision):
    changed = db.execute(update(Evidence).where(Evidence.id == evidence.id, Evidence.metadata_revision == expected_revision)
                         .values(metadata_revision=expected_revision + 1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise HTTPException(409, "Metadata changed; reload evidence and use its current revision")
    db.refresh(evidence)


def annotate(db, evidence_id, actor, payload):
    evidence = require_evidence(db, evidence_id, actor.id)
    claim_revision(db, evidence, payload.expected_revision)
    operation_id = uuid4()
    custody.ensure_baseline(db, evidence, operation_id)
    changes = {}
    for field in ('display_title', 'review_state'):
        if field in payload.model_fields_set:
            changes[field] = {'before': getattr(evidence, field), 'after': getattr(payload, field)}
            setattr(evidence, field, getattr(payload, field))
    if 'tags' in payload.model_fields_set:
        before = db.scalars(select(EvidenceTag.tag).where(EvidenceTag.evidence_id == evidence.id).order_by(EvidenceTag.tag)).all()
        db.execute(delete(EvidenceTag).where(EvidenceTag.evidence_id == evidence.id))
        db.add_all([EvidenceTag(evidence_id=evidence.id, tag=tag) for tag in payload.tags])
        changes['tags'] = {'before': before, 'after': payload.tags}
    db.flush()
    custody.append_event(db, evidence, event_type='annotations_updated', actor_user=actor,
                         operation_id=operation_id, details={'changes': changes, 'metadata_revision': evidence.metadata_revision})
    return evidence


def add_note(db, evidence_id, actor, payload):
    evidence = require_evidence(db, evidence_id, actor.id)
    claim_revision(db, evidence, payload.expected_revision)
    operation_id = uuid4()
    custody.ensure_baseline(db, evidence, operation_id)
    note = EvidenceNote(id=uuid4(), evidence_id=evidence.id, author_id=actor.id,
                        author_label=actor.display_name, body=payload.body)
    db.add(note)
    db.flush()
    custody.append_event(db, evidence, event_type='note_added', actor_user=actor, operation_id=operation_id,
                         details={'note_id': str(note.id), 'body_sha256': hashlib.sha256(note.body.encode()).hexdigest(),
                                  'metadata_revision': evidence.metadata_revision})
    return note, evidence.metadata_revision
