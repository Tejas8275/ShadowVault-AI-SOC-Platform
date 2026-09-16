import asyncio
import json
import logging
from pathlib import Path
import unittest

from fastapi.testclient import TestClient
from app.core.config import Settings
from app.core.privacy import ResponsePrivacy, SafeServerFormatter
from app.main import create_app


class PrivacyTests(unittest.TestCase):
    def app(self):
        return create_app(Settings(_env_file=None, environment='test', database_url='sqlite://', ai_enabled=False))

    def private(self, response):
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
        self.assertEqual(response.headers['referrer-policy'], 'no-referrer')
        self.assertEqual(response.headers['x-frame-options'], 'DENY')

    def test_success_denial_not_found_and_preflight_are_private(self):
        with TestClient(self.app()) as client:
            for path, status in [('/api/v1/health', 200), ('/api/v2/investigation/evidence', 401), ('/api/missing', 404)]:
                response = client.get(path)
                self.assertEqual(response.status_code, status)
                self.private(response)
            self.assertEqual(client.get('/api/v2/investigation/evidence').headers['www-authenticate'], 'Bearer')
            response = client.options('/api/v1/health', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'GET'})
            self.assertEqual(response.headers['access-control-allow-origin'], 'http://localhost:5173')
            self.private(response)

    def test_invalid_body_never_echoes_secret_or_dynamic_keys(self):
        with TestClient(self.app()) as client:
            response = client.post('/api/v1/auth/login', json={'email': {'PRIVATE-CANARY': 'SECRET'}, 'password': ''})
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json(), {'detail': 'Request validation failed'})
            self.private(response)
            response = client.post('/api/v1/auth/login', content='{"PRIVATE-CANARY":', headers={'Content-Type': 'application/json'})
            self.assertEqual(response.status_code, 422)
            self.assertNotIn('PRIVATE-CANARY', response.text)

    def test_unexpected_error_is_generic_and_not_logged(self):
        app = self.app()
        @app.get('/api/test-failure')
        def fail():
            raise RuntimeError('PRIVATE-CANARY /private/file SECRET')
        with TestClient(app) as client, self.assertLogs('app.core.privacy', level='ERROR') as captured:
            response = client.get('/api/test-failure?secret=PRIVATE-CANARY')
        self.assertEqual(response.status_code, 500)
        self.private(response)
        self.assertEqual(response.json(), {'detail': 'Request could not be completed'})
        self.assertNotIn('PRIVATE-CANARY', repr(captured.output))
        self.assertIsNone(captured.records[0].exc_info)

    def test_partial_stream_does_not_send_second_response_or_hide_failure(self):
        messages = []
        async def inner(scope, receive, send):
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'part', 'more_body': True})
            raise OSError('PRIVATE-CANARY')
        async def receive():
            return {'type': 'http.disconnect'}
        async def send(message):
            messages.append(message)
        with self.assertLogs('app.core.privacy', level='ERROR'), self.assertRaisesRegex(RuntimeError, '^Response interrupted$'):
            asyncio.run(ResponsePrivacy(inner)({'type': 'http', 'path': '/api/test'}, receive, send))
        self.assertEqual(len(messages), 2)
        self.assertTrue(messages[1]['more_body'])

    def test_formatter_never_interpolates_arguments_or_traceback(self):
        record = logging.LogRecord('PRIVATE-CANARY', logging.ERROR, '/SECRET/file', 10,
                                   'PRIVATE %s', ('TOKEN',), (ValueError, ValueError('SECRET'), None))
        record.stack_info = 'PRIVATE STACK'
        self.assertEqual(SafeServerFormatter().format(record), 'server_event level=40')
        config = json.loads(Path('backend/logging.json').read_text())
        self.assertEqual(config['loggers']['uvicorn.access']['handlers'], [])
        self.assertFalse(config['loggers']['uvicorn.access']['propagate'])
        self.assertEqual(config['formatters']['private']['()'], 'app.core.privacy.SafeServerFormatter')

    def test_oversize_and_placeholder_contract_remain_private(self):
        with TestClient(self.app()) as client:
            response = client.post('/api/v1/agents', content=b'x' * (128 * 1024 + 1))
            self.assertEqual(response.status_code, 413)
            self.private(response)
            response = client.post('/api/v1/auth/login', json={'email': 'user@example.test', 'password': 'placeholder'})
            self.assertEqual(response.status_code, 501)
            self.private(response)
