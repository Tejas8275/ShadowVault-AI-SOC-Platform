"""Response privacy and deliberately content-free operational diagnostics."""
import logging

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class SafeServerFormatter(logging.Formatter):
    """Do not interpolate arbitrary messages, arguments, paths or tracebacks."""

    def format(self, record):
        return f"server_event level={record.levelno}"


async def validation_failure(_request, _error):
    # Even error locations/context can contain user-controlled keys and values.
    return JSONResponse({'detail': 'Request validation failed'}, status_code=422)


class ResponsePrivacy:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        started = False
        private = scope.get('path', '').startswith('/api/') or scope.get('path') == '/health'

        async def protected_send(message):
            nonlocal started
            if message['type'] == 'http.response.start':
                started = True
                if private:
                    message = dict(message, headers=list(message.get('headers', [])))
                    headers = MutableHeaders(scope=message)
                    headers['Cache-Control'] = 'no-store'
                    headers['Pragma'] = 'no-cache'
                    headers['X-Content-Type-Options'] = 'nosniff'
                    headers['Referrer-Policy'] = 'no-referrer'
                    headers['X-Frame-Options'] = 'DENY'
            await send(message)

        try:
            await self.app(scope, receive, protected_send)
        except Exception:
            # Dependencies unwind/rollback before reaching this boundary. Never
            # log the exception, request, query, headers or body.
            logger.error('Request failed')
            if started:
                # Cannot replace a partial attachment with JSON or claim success.
                raise RuntimeError('Response interrupted') from None
            await JSONResponse({'detail': 'Request could not be completed'}, status_code=500)(
                scope, receive, protected_send)
