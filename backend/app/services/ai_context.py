"""AI allowlist layered over the existing authorized report snapshot."""
import hashlib
import json
from dataclasses import dataclass
from fastapi import HTTPException
from app.schemas.ai_briefing import BriefingSource, ModelSelection

MAX_CONTEXT_BYTES = 64 * 1024
MAX_OUTPUT_BYTES = 32 * 1024
MAX_SOURCES = 128
MAX_FIELD_CHARACTERS = 2048
FIELDS = {
    'Evidence records': {'filename','display_title','size_bytes','sha256','created_at','collected_at',
        'verified_at','verification_status','review_state','metadata_revision','tags',
        'custody_sequence','integrity_result','integrity_checked_at'},
    'Timeline observations': {'title','description','occurred_at','reported_time','created_at','origin','source','source_locator'},
    'Recorded indicators': {'kind','raw_value','normalized_value','source_kind','source_locator','created_at','supersedes_id','superseded_by_id'},
    'Evidence custody records': {'sequence','event_type','actor_type','recorded_at'},
    'Case history': {'revision','event_type','recorded_at','source',
        'title before','title after','description before','description after',
        'severity before','severity after','status before','status after'},
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


@dataclass(frozen=True)
class Context:
    data: str
    digest: str
    sources: dict[str, BriefingSource]


def build(draft):
    case_fields = draft.case.model_dump(mode='json', include={
        'title','description','severity','status','revision','created_at','updated_at'})
    rows = [BriefingSource(citation=f'incident:{draft.case.id}', section='Case metadata', fields=case_fields)]
    for section in draft.sections:
        if section.title not in FIELDS:
            continue  # No note bodies, raw files, identity fields or arbitrary report fields.
        for row in section.records:
            rows.append(BriefingSource(citation=row.citation, section=section.title,
                evidence_id=row.evidence_id, fields={k:v for k,v in row.fields.items() if k in FIELDS[section.title]}))
    if len(rows) > MAX_SOURCES or any(isinstance(v, str) and len(v) > MAX_FIELD_CHARACTERS
                                    for row in rows for v in row.fields.values()):
        raise HTTPException(413, 'AI metadata source or field limit exceeded')
    if len({row.citation for row in rows}) != len(rows):
        raise HTTPException(503, 'AI context unavailable')
    sources = {f'S{i}': row for i, row in enumerate(rows, 1)}
    aliases = {row.citation: alias for alias, row in sources.items()}
    provider_rows = []
    for alias, row in sources.items():
        fields = dict(row.fields)
        for key in ('supersedes_id','superseded_by_id'):
            if fields.get(key):
                target = aliases.get(f'indicator:{fields[key]}')
                if target is None: raise HTTPException(503, 'AI context unavailable')
                fields[key] = target
        provider_rows.append({'alias':alias, 'section':row.section, 'fields':fields,
            'evidence_source':aliases.get(f'evidence:{row.evidence_id}') if row.evidence_id else None})
    data = canonical({'context_version':1, 'untrusted_records':provider_rows})
    if len(data.encode('utf-8')) > MAX_CONTEXT_BYTES:
        raise HTTPException(413, 'AI metadata context exceeds limits')
    manifest = canonical([row.model_dump(mode='json') for row in rows])
    return Context(data, hashlib.sha256(manifest.encode('utf-8')).hexdigest(), sources)


def resolve(context, raw):
    if not isinstance(raw, str) or len(raw.encode('utf-8')) > MAX_OUTPUT_BYTES:
        raise ValueError('Invalid output size')
    # Duplicate JSON keys are not an alternate way to override the selection.
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('Duplicate key')
            result[key] = value
        return result
    selected = ModelSelection.model_validate(json.loads(raw, object_pairs_hook=unique))
    if len(set(selected.sources)) != len(selected.sources): raise ValueError('Duplicate source')
    if any(alias not in context.sources for alias in selected.sources): raise ValueError('Unknown source')
    by_citation = {row.citation: row for row in context.sources.values()}
    result = [context.sources[alias].model_copy(deep=True) for alias in selected.sources]
    seen = {row.citation for row in result}
    # Include the full authorized correction chain, even when not selected by AI.
    for row in result:
        for key in ('supersedes_id', 'superseded_by_id'):
            if row.fields.get(key):
                citation = f'indicator:{row.fields[key]}'
                partner = by_citation.get(citation)
                if partner is None or partner.evidence_id != row.evidence_id: raise ValueError('Invalid correction')
                if citation not in seen:
                    seen.add(citation)
                    result.append(partner.model_copy(update={'selection':'correction_context'}, deep=True))
        if len(result) > 40: raise ValueError('Correction context exceeds limits')
    return result
