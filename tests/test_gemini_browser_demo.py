import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from pydantic import SecretStr
from fastapi.testclient import TestClient
from app.core.security import token_digest
from app.services.ai_model import SYSTEM_INSTRUCTIONS
from briefing_fixture import FixtureProvider
from gemini_browser_demo import BrowserEvaluationProvider, demo_app
from openai_synthetic_data import CASE_IDS, fixed_context


class BrowserDemoTests(unittest.TestCase):
    def test_authorized_reads_and_briefing_but_no_mutations(self):
        token = 'sv_operator_' + 'demo-test-only'
        app = demo_app(SecretStr(token_digest(token)), FixtureProvider())
        base = '/api/v2/investigation'
        with TestClient(app) as client:
            headers = {'Authorization': 'Bearer ' + token}
            self.assertEqual(client.get(base+'/incidents').status_code, 401)
            response = client.get(base+'/incidents', headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['total'], 4)
            engine = app.state.session_factory.kw['bind']
            self.assertIn(engine.url.database, (None, '', ':memory:'))
            for path, method in [(base+'/incidents', 'POST'), (base+'/incidents/'+str(CASE_IDS['A']), 'PATCH'),
                                 ('/api/v1/agents', 'POST'), (base+'/evidence/00000000-0000-0000-0000-0000000003e9/download', 'POST')]:
                self.assertEqual(client.request(method, path, headers=headers, json={}).status_code, 403)
            path = base+'/incidents/'+str(CASE_IDS['A'])+'/ai-briefing'
            self.assertEqual(client.post(path, json={'schema_version': 1}).status_code, 401)
            self.assertEqual(client.post(path, headers=headers, json={'schema_version': 1}).status_code, 200)
            self.assertEqual(client.get(base+'/incidents/00000000-0000-0000-0000-000000009999', headers=headers).status_code, 404)

    def test_nonfixture_never_reaches_adapter_and_retries_are_new_explicit_calls(self):
        async def run():
            provider = BrowserEvaluationProvider(SecretStr('synthetic-key'))
            with patch('gemini_browser_demo.SyntheticGeminiProvider') as adapter:
                with self.assertRaises(ValueError):
                    await provider.count_input_tokens(instructions=SYSTEM_INSTRUCTIONS, data='real-user-input')
                adapter.assert_not_called()
                child = adapter.return_value
                child.count_input_tokens = AsyncMock(return_value=10)
                child.select_sources = AsyncMock(return_value='{"sources":["S1"]}')
                data = fixed_context('A').data
                await provider.count_input_tokens(instructions=SYSTEM_INSTRUCTIONS, data=data)
                with self.assertRaises(ValueError):
                    await provider.select_sources(instructions=SYSTEM_INSTRUCTIONS, data=fixed_context('B').data, max_output_bytes=32768,max_output_tokens=1024)
                child.select_sources.assert_not_called()
                await provider.select_sources(instructions=SYSTEM_INSTRUCTIONS, data=data,max_output_bytes=32768,max_output_tokens=1024)
                with self.assertRaises(ValueError):
                    await provider.select_sources(instructions=SYSTEM_INSTRUCTIONS,data=data,max_output_bytes=32768,max_output_tokens=1024)
                await provider.count_input_tokens(instructions=SYSTEM_INSTRUCTIONS, data=data)
                self.assertEqual(adapter.call_count, 2)
        asyncio.run(run())
