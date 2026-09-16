"""A custody-recorded attachment operation; no public content URLs or range support."""
import asyncio
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import StreamingResponse
from app.core.security import Credentials, Database, Operator
from app.services import evidence_retrieval

router = APIRouter(prefix='/api/v2/investigation', tags=['investigation'])


class PreparedDownload(StreamingResponse):
    def __init__(self, copy, size, evidence_id, slots, timeout):
        self.copy, self.slots, self.timeout = copy, slots, timeout
        super().__init__(self.chunks(), media_type='application/octet-stream', headers={
            'Content-Length': str(size), 'Content-Disposition': f'attachment; filename="evidence-{evidence_id}.bin"',
            'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Accept-Ranges': 'none'})

    def chunks(self):
        while chunk := self.copy.read(64 * 1024):
            yield chunk

    async def __call__(self, scope, receive, send):
        try:
            async with asyncio.timeout(self.timeout):
                await super().__call__(scope, receive, send)
        finally:
            try:
                self.copy.close()
            finally:
                self.slots.release()


@router.post('/evidence/{evidence_id}/download', response_class=StreamingResponse,
             responses={200: {'content': {'application/octet-stream': {}}}})
def download(evidence_id: UUID, request: Request, db: Database, actor: Operator, credentials: Credentials):
    if 'range' in request.headers:
        raise HTTPException(416, 'Resumable downloads are not supported')
    slots = request.app.state.retrieval_slots
    if not slots.acquire(blocking=False):
        raise HTTPException(429, 'Retrieval capacity reached', headers={'Retry-After': '5'})
    copy = None
    try:
        copy, size = evidence_retrieval.prepare(db, request, credentials, actor, evidence_id)
        return PreparedDownload(copy, size, evidence_id, slots, request.app.state.settings.retrieval_timeout_seconds)
    except BaseException as error:
        try:
            if copy is not None:
                copy.close()
        except OSError:
            # Preserve the original sanitized request failure if cleanup also fails.
            pass
        finally:
            try:
                db.rollback()
            finally:
                slots.release()
        if isinstance(error, (OSError, SQLAlchemyError)):
            raise HTTPException(503, 'Evidence retrieval is unavailable') from None
        raise
