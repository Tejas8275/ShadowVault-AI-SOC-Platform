"""Bounded SQLite read snapshot. Never reads blobs or records custody/history."""
import json
import time
from datetime import datetime
from enum import Enum
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from app.models import Evidence, EvidenceNote, EvidenceTag, CustodyEvent, CaseHistoryEvent, TimelineEvent, IndicatorObservation
from app.models.common import utc_now
from app.schemas.case_report import CaseReportDraft, ReportRecord, ReportSection
from app.schemas.incident import IncidentResponse
from app.services import evidence_query, incidents, timeline, indicators

MAX_ROWS = 2000
MAX_BYTES = 2 * 1024 * 1024
MAX_SECONDS = 5

LIMITATIONS = [
    'Draft of recorded information, not an AI conclusion, threat verdict or certified forensic report.',
    'Source citations refer only to stored records. Source text is investigator-supplied and has not been externally verified.',
    'Complete authorized scope at preparation time, independent of workspace filters; hidden records are excluded.',
    'Initial verification concerns upload hash/size. Subsequent integrity checks are not executed by this report.',
    'Custody entries and heads are recorded metadata; no chain verification runs here. Tracking may start after acquisition.',
    'Retrieval prepared means a verified copy was prepared, not that delivery or local saving succeeded.',
    'Timeline occurrence and recording times differ. Indicators are observations; originals and corrections are retained.',
    'Case history starts at the earliest included tracked revision; earlier changes are not reconstructed.',
    'Private storage keys, acquisition filesystem paths and custody detail payloads are excluded. Free text may still contain sensitive information; review before saving.',
    'Transient snapshot only: no server-side report storage or later retrieval by report ID. A saved local copy is outside access revocation.',
]


def value(item):
    if item is None or isinstance(item, (str, int)):
        return item
    if isinstance(item, Enum):
        return item.value
    if isinstance(item, datetime):
        return item.isoformat()
    if isinstance(item, UUID):
        return str(item)
    return json.dumps(item, ensure_ascii=False, sort_keys=True)


def build(db, incident_id, actor_id):
    # Operator lookup may have started a logical Session transaction. Explicit
    # BEGIN is required for a multi-SELECT snapshot with sqlite3 legacy mode.
    db.rollback()
    connection = db.connection()
    if connection.dialect.name != 'sqlite':
        raise HTTPException(503, 'Report snapshots require the reviewed SQLite deployment')
    raw = connection.connection.driver_connection
    deadline = time.monotonic() + MAX_SECONDS
    raw.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    try:
        connection.exec_driver_sql('BEGIN')
        record = incidents.require_incident(db, incident_id, actor_id)
        case = IncidentResponse.model_validate(record)
        sections = []
        remaining = MAX_ROWS

        def section(title, query, fields, kind, evidence=False, extras=None):
            nonlocal remaining
            if time.monotonic() > deadline:
                raise HTTPException(503, 'Report preparation timed out')
            rows = db.scalars(query.limit(remaining + 1)).all()
            if len(rows) > remaining:
                raise HTTPException(413, 'Case exceeds the complete report row limit')
            remaining -= len(rows)
            entries = []
            for row in rows:
                details = {field: value(getattr(row, field)) for field in fields}
                if extras:
                    details.update(extras(row))
                entries.append(ReportRecord(citation=f'{kind}:{row.id}',
                    evidence_id=row.id if kind == 'evidence' else getattr(row, 'evidence_id', None) if evidence else None,
                    fields=details))
            sections.append(ReportSection(title=title, records=entries))
            return rows

        scope = evidence_query.authorized_query(actor_id).where(Evidence.incident_id == incident_id)
        ids = scope.with_only_columns(Evidence.id)
        evidence = section('Evidence records', scope.order_by(Evidence.created_at, Evidence.id),
            ['filename', 'display_title', 'size_bytes', 'sha256', 'created_at', 'collected_at', 'verified_at',
             'verification_status', 'review_state', 'metadata_revision', 'collection_job_id', 'collection_item_id',
             'custody_sequence', 'custody_head_hash'], 'evidence')
        # Bound tag rows as well; never serialize arbitrary ORM attributes.
        tags = db.execute(select(EvidenceTag.evidence_id, EvidenceTag.tag).where(EvidenceTag.evidence_id.in_(ids))
                          .order_by(EvidenceTag.evidence_id, EvidenceTag.tag).limit(remaining + 1)).all()
        if len(tags) > remaining:
            raise HTTPException(413, 'Case exceeds the complete report row limit')
        remaining -= len(tags)
        tag_map = {}
        for eid, tag in tags:
            tag_map.setdefault(eid, []).append(tag)
        checks = evidence_query.summaries(db, evidence)
        for entry, item in zip(sections[0].records, checks):
            entry.fields.update(tags=', '.join(tag_map.get(item.id, [])), integrity_result=item.integrity_result,
                                integrity_checked_at=value(item.integrity_checked_at))
        section('Investigator notes', select(EvidenceNote).where(EvidenceNote.evidence_id.in_(ids))
                .order_by(EvidenceNote.created_at, EvidenceNote.id),
                ['body', 'author_id', 'author_label', 'created_at'], 'note', True)
        section('Timeline observations', timeline.authorized_query(actor_id).where(TimelineEvent.incident_id == incident_id)
                .order_by(TimelineEvent.occurred_at, TimelineEvent.id),
                ['title', 'description', 'occurred_at', 'reported_time', 'created_at', 'origin', 'source',
                 'source_locator', 'recorded_by_id', 'recorded_by_label'], 'timeline', True)
        observations = section('Recorded indicators', indicators.scoped(actor_id).where(IndicatorObservation.incident_id == incident_id)
                .order_by(IndicatorObservation.created_at, IndicatorObservation.id),
                ['kind', 'raw_value', 'normalized_value', 'source_kind', 'source_locator', 'created_by_id',
                 'actor_label', 'created_at'], 'indicator', True)
        visible = {row.id: row for row in observations}
        successors = {row.supersedes_id: row.id for row in observations if row.supersedes_id in visible
                      and visible[row.supersedes_id].evidence_id == row.evidence_id}
        for entry, row in zip(sections[-1].records, observations):
            predecessor = row.supersedes_id if row.supersedes_id in visible and visible[row.supersedes_id].evidence_id == row.evidence_id else None
            entry.fields.update(supersedes_id=value(predecessor), superseded_by_id=value(successors.get(row.id)))
        section('Evidence custody records', select(CustodyEvent).where(CustodyEvent.evidence_id.in_(ids))
                .order_by(CustodyEvent.evidence_id, CustodyEvent.sequence),
                ['sequence', 'event_type', 'actor_type', 'actor_user_id', 'actor_label', 'recorded_at',
                 'previous_hash', 'event_hash'], 'custody', True)
        section('Case history', select(CaseHistoryEvent).where(CaseHistoryEvent.incident_id == incident_id)
                .order_by(CaseHistoryEvent.revision),
                ['revision', 'event_type', 'actor_label', 'actor_user_id', 'recorded_at', 'source'], 'history',
                extras=lambda row: {f'{field} {side}': change.get(side) for field, change in row.changes.items()
                                    if field in ('title', 'description', 'severity', 'status') for side in ('before', 'after')})
        draft = CaseReportDraft(generated_at=utc_now(), case=case, sections=sections,
            summary={part.title: len(part.records) for part in sections}, limitations=LIMITATIONS)
        if len(draft.model_dump_json().encode('utf-8')) > MAX_BYTES:
            raise HTTPException(413, 'Case exceeds the complete report byte limit')
        if time.monotonic() > deadline:
            raise HTTPException(503, 'Report preparation timed out')
        return draft
    finally:
        raw.set_progress_handler(None, 0)
        db.rollback()


def recheck_scope(db, draft, actor_id):
    incidents.require_incident(db, draft.case.id, actor_id)
    ids = [row.evidence_id for row in draft.sections[0].records]
    visible = set(db.scalars(evidence_query.authorized_query(actor_id).where(Evidence.id.in_(ids)).with_only_columns(Evidence.id)))
    if visible != set(ids):
        raise HTTPException(404, 'Case report no longer available')
