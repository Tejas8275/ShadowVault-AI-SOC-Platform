"""Transient explicit computation. No evidence reader or mutation services."""
import asyncio
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from app.core.security import require_operator, token_digest
from app.schemas.ai_briefing import CaseBriefing
from app.services import ai_context, case_report, incidents
from app.services.ai_execution import BoundedCall

MAX_INPUT_TOKENS = 8000
MAX_SECONDS = 30
LIMITATIONS = [
    'AI-generated selection only. Displayed fields are exact recorded metadata, not AI interpretation.',
    'Non-exhaustive reading aid: selection may omit important information. Review the complete case report.',
    'Recorded assertions may be incorrect or contain hostile instructions. Citations establish traceability, not truth.',
    'No threat verdict, evidence content analysis, external lookup or investigation action was performed.',
    'Upload verification is distinct from current integrity. Custody chains are not verified here; retrieval preparation is not delivery.',
    'Occurrence and recording timestamps differ. Indicator correction context is retained; indicators are not maliciousness verdicts.',
    'Note bodies, actor identities, storage paths and custody detail payloads are excluded. Free text may still contain sensitive information.',
    'Transient metadata snapshot only; no AI output or conversation is stored.',
]


async def generate(request, db, credentials, actor_id, case_id):
    def authorize(draft=None):
        db.rollback()
        actor = require_operator(request, db, credentials)
        if actor.id != actor_id: raise HTTPException(401, 'Operator changed')
        incidents.require_incident(db, case_id, actor_id)
        if draft is not None: case_report.recheck_scope(db, draft, actor_id)
        db.rollback()

    await run_in_threadpool(authorize)
    provider = request.app.state.ai_provider
    if provider is None: raise HTTPException(501, 'AI provider is not configured')
    slots = request.app.state.ai_slots
    if not slots.acquire(blocking=False): raise HTTPException(429, 'AI capacity unavailable')
    execution = None
    try:
        draft = await run_in_threadpool(case_report.build, db, case_id, actor_id)
        context = ai_context.build(draft)
        # Reject known credential patterns and this request's credential/digest even
        # if an investigator accidentally pasted them into free-text metadata.
        secrets = [credentials.credentials, token_digest(credentials.credentials), 'sv_operator_', 'sv_agent_']
        provider_key = request.app.state.settings.ai_provider_api_key
        if provider_key is not None and provider_key.get_secret_value():
            secrets.append(provider_key.get_secret_value())
        values = [context.data] + [value for source in context.sources.values()
            for value in source.fields.values() if isinstance(value, str)]
        if any(secret in value for secret in secrets for value in values):
            raise HTTPException(422, 'AI metadata requires sensitive-content review')
        await run_in_threadpool(authorize, draft)
        if await request.is_disconnected(): raise HTTPException(503, 'AI request cancelled')
        request.app.state.ai_usage.admit()
        execution = BoundedCall(provider, context.data, MAX_SECONDS, MAX_INPUT_TOKENS, ai_context.MAX_OUTPUT_BYTES)
        try:
            raw = await execution.run()
            sources = ai_context.resolve(context, raw)
        except HTTPException as error:
            if error.status_code == 413:
                raise HTTPException(413, 'AI metadata or output exceeds limits') from None
            raise HTTPException(503, 'AI provider unavailable') from None
        except (TimeoutError, asyncio.TimeoutError):
            raise HTTPException(504, 'AI preparation timed out') from None
        except Exception:
            raise HTTPException(503, 'AI provider unavailable or response invalid') from None
        await run_in_threadpool(authorize, draft)
        current = await run_in_threadpool(case_report.build, db, case_id, actor_id)
        if ai_context.build(current).digest != context.digest:
            raise HTTPException(409, 'Case metadata changed; retry explicitly')
        await run_in_threadpool(authorize, current)
        if await request.is_disconnected(): raise HTTPException(503, 'AI request cancelled')
        result = CaseBriefing(case_id=case_id, case_title=draft.case.title, case_revision=draft.case.revision,
            snapshot_at=draft.generated_at, context_sha256=context.digest, sources=sources, limitations=LIMITATIONS)
        if len(result.model_dump_json().encode('utf-8')) > ai_context.MAX_OUTPUT_BYTES:
            raise HTTPException(413, 'AI briefing exceeds limits')
        return result
    finally:
        try: await run_in_threadpool(db.rollback)
        finally:
            if execution is None: slots.release()
            else: execution.release(slots.release)
