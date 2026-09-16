"""Bound collection JSON before parsing, and bound raw upload bodies while receiving."""
from fastapi import HTTPException
from starlette.responses import JSONResponse


class CollectionBodyLimit:
    def __init__(self, app, max_upload_bytes):
        self.app = app
        self.max_upload_bytes = max_upload_bytes

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        if scope['type'] != 'http' or not path.startswith(('/api/v1/agents', '/api/v1/collection-jobs', '/api/v2/investigation')):
            return await self.app(scope, receive, send)
        limit = self.max_upload_bytes if scope['method'] == 'PUT' else 128 * 1024
        headers = dict(scope.get('headers', []))
        if b'content-length' in headers:
            try:
                length = int(headers[b'content-length'])
                if length < 0:
                    raise ValueError()
            except ValueError:
                return await JSONResponse({'detail': 'Invalid Content-Length'}, status_code=400)(scope, receive, send)
            if length > limit:
                return await JSONResponse({'detail': 'Request body exceeds server limit'}, status_code=413)(scope, receive, send)
        received = 0

        async def bounded_receive():
            nonlocal received
            message = await receive()
            if message['type'] == 'http.request':
                received += len(message.get('body', b''))
                if received > limit:
                    raise HTTPException(413, 'Request body exceeds server limit')
            return message

        await self.app(scope, bounded_receive, send)
