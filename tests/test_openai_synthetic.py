"""Deterministic SDK transport tests. No live OpenAI calls or real data."""
import asyncio
from contextlib import redirect_stdout
import io
import json
import unittest
from unittest.mock import patch

import httpx2
from pydantic import SecretStr
from sqlalchemy import select
from app.models import Incident
from app.services.ai_model import SYSTEM_INSTRUCTIONS
from app.services.ai_context import resolve
from app.services.ai_adapter import CommandProvider
from app.services.ai_execution import BoundedCall
from openai_synthetic_adapter import evaluate, BoundedTransport, MAX_HTTP_BYTES, MODEL, safe_failure
from openai_synthetic_data import fixed_context, CASE_IDS, OTHER_ACTOR, TOKEN
from evaluate_openai import SyntheticOpenAIProvider, synthetic_client, main


def request_for(scenario='A', operation='count'):
    request = dict(operation=operation, instructions=SYSTEM_INSTRUCTIONS, data=fixed_context(scenario).data)
    if operation == 'select':
        request.update(max_output_bytes=32768, max_output_tokens=1024)
    return request


def response_for(text='{"sources":["S1","S2","S8"]}'):
    return dict(status='completed', model=MODEL, output=[dict(type='message', role='assistant',
        status='completed', content=[dict(type='output_text', text=text, annotations=[])])],
        usage=dict(input_tokens=1500, output_tokens=20, total_tokens=1520))


class SDKTests(unittest.TestCase):
    def test_safe_diagnostics_never_echo_exception_or_http_body(self):
        from openai import BadRequestError
        request=httpx2.Request('POST','https://api.openai.com/v1/responses',
                               headers={'Authorization':'Bearer PRIVATE'})
        error=BadRequestError('PRIVATE',response=httpx2.Response(400,request=request),
                              body={'secret':'PRIVATE'})
        self.assertEqual(safe_failure(error),{'evaluation_error':'http_error','http_status':400})
        self.assertEqual(safe_failure(ValueError('PRIVATE')),{'evaluation_error':'validation_rejected'})
        self.assertNotIn('PRIVATE',json.dumps(safe_failure(error)))

    def fake(self, result, status=200, headers=None):
        self.calls = []
        def handler(request):
            self.calls.append(request)
            raw = json.dumps(result).encode() if not isinstance(result, bytes) else result
            return httpx2.Response(status, headers=headers or {'content-type': 'application/json'},
                                   stream=httpx2.ByteStream(raw))
        return httpx2.MockTransport(handler)

    def test_count_and_generation_use_identical_context_schema_and_no_tools(self):
        transport = self.fake({'object': 'response.input_tokens', 'input_tokens': 1500})
        self.assertEqual(evaluate(request_for(), 'A', 'test-key', transport=transport), {'input_tokens': 1500})
        count_request = self.calls[0]
        count = json.loads(count_request.content)
        self.assertEqual(str(count_request.url), 'https://api.openai.com/v1/responses/input_tokens')
        transport = self.fake(response_for())
        selected = evaluate(request_for(operation='select'), 'A', 'test-key', transport=transport)
        generation = json.loads(self.calls[0].content)
        for key, value in count.items():
            self.assertEqual(generation[key], value, key)
        self.assertFalse(generation['store']); self.assertFalse(generation['background'])
        self.assertFalse(generation['stream']); self.assertEqual(generation['tools'], [])
        self.assertEqual(generation['max_output_tokens'], 1024)
        self.assertEqual(generation['model'], MODEL)
        self.assertNotIn('test-key', json.dumps(generation))
        self.assertEqual(self.calls[0].headers['authorization'], 'Bearer test-key')
        self.assertEqual(self.calls[0].headers['accept-encoding'], 'identity')
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(resolve(fixed_context('A'), selected['selection'])), 3)

    def test_non_synthetic_and_cross_case_payload_rejected_before_network(self):
        for alteration in ('data', 'instructions', 'extra'):
            request = request_for()
            request[alteration] = 'REAL PRIVATE DATA'
            transport = self.fake({})
            with self.assertRaises(ValueError): evaluate(request, 'A', 'test-key', transport=transport)
            self.assertEqual(self.calls, [])
        with self.assertRaises(ValueError):
            evaluate(request_for('B'), 'A', 'test-key', transport=self.fake({}))
        self.assertEqual(self.calls, [])

    def test_missing_key_wrong_model_limits_and_secret_rejected_locally(self):
        for key, model in [('', MODEL), ('test-key', 'other-model'), ('Synthetic', MODEL)]:
            with self.assertRaises(ValueError):
                evaluate(request_for(), 'A', key, model, transport=self.fake({}))
            self.assertEqual(self.calls, [])
        request = request_for(operation='select'); request['max_output_tokens'] = 9999
        with self.assertRaises(ValueError): evaluate(request, 'A', 'test-key', transport=self.fake({}))
        self.assertEqual(self.calls, [])

    def test_invalid_counts_are_rejected(self):
        for result in [{'object':'response.input_tokens','input_tokens':True},
                       {'object':'response.input_tokens','input_tokens':0},
                       {'object':'other','input_tokens':5},
                       b'{"object":"response.input_tokens","input_tokens":1,"input_tokens":2}']:
            with self.assertRaises(ValueError):
                evaluate(request_for(), 'A', 'test-key', transport=self.fake(result))

    def test_unknown_duplicate_cross_case_and_prose_outputs_rejected(self):
        for raw in ['not json', '{"sources":["S999"]}', '{"sources":["S1","S1"]}',
                    '{"sources":["incident:00000000-0000-0000-0000-0000000007d0"]}',
                    '{"sources":["S1"],"verdict":"malicious"}', '{"sources":[]}']:
            with self.assertRaises((ValueError, TypeError)):
                evaluate(request_for(operation='select'), 'A', 'test-key', transport=self.fake(response_for(raw)))

    def test_refusal_incomplete_tools_and_usage_excess_rejected(self):
        variants = []
        item = response_for(); item['status']='incomplete'; variants.append(item)
        item = response_for(); item['model']='other'; variants.append(item)
        item = response_for(); item['output'][0]['type']='function_call'; variants.append(item)
        item = response_for(); item['output'][0]['content'][0]['type']='refusal'; variants.append(item)
        item = response_for(); item['usage']['input_tokens']=9000; variants.append(item)
        for item in variants:
            with self.assertRaises(ValueError):
                evaluate(request_for(operation='select'), 'A', 'test-key', transport=self.fake(item))

    def test_http_failure_rate_limit_and_timeout_have_no_retry(self):
        for status in (401,429,500,503):
            with self.assertRaises(Exception):
                evaluate(request_for(), 'A', 'test-key', transport=self.fake({'error':'private'}, status))
            self.assertEqual(len(self.calls),1)
        calls=[]
        def timeout(request):
            calls.append(request); raise httpx2.ReadTimeout('private timeout')
        with self.assertRaises(Exception):
            evaluate(request_for(), 'A', 'test-key', transport=httpx2.MockTransport(timeout))
        self.assertEqual(len(calls),1)

    def test_transport_rejects_redirect_encoding_oversize_and_second_request(self):
        for result,status,headers in [(b'',302,{'location':'https://example.test'}),
                (b'compressed',200,{'content-encoding':'gzip'}),
                (b'x'*(MAX_HTTP_BYTES+1),500,{}), (b'',200,{'content-length':str(MAX_HTTP_BYTES+1)})]:
            with self.assertRaises(Exception):
                evaluate(request_for(), 'A', 'test-key', transport=self.fake(result,status,headers))
            self.assertEqual(len(self.calls),1)
        transport=BoundedTransport(self.fake({}), 'count')
        request=httpx2.Request('POST','https://api.openai.com/v1/responses/input_tokens')
        transport.handle_request(request).close()
        with self.assertRaises(ValueError): transport.handle_request(request)
        with self.assertRaises(ValueError):
            BoundedTransport(self.fake({}),'count').handle_request(httpx2.Request('POST','http://example.test'))
        self.assertEqual(self.calls,[])


class SyntheticBoundaryTests(unittest.TestCase):
    def test_sdk_through_endpoint_validates_citations_and_preserves_every_table(self):
        from sqlalchemy import MetaData
        provider = SyntheticOpenAIProvider('A', SecretStr('test-key'))
        requests = []
        async def call(operation, instructions, data, limit, **options):
            def handler(request):
                requests.append(request)
                result = ({'object':'response.input_tokens','input_tokens':1500}
                          if operation == 'count' else response_for())
                return httpx2.Response(200, stream=httpx2.ByteStream(json.dumps(result).encode()))
            return json.dumps(evaluate(dict(operation=operation,instructions=instructions,data=data,**options),
                'A','test-key',transport=httpx2.MockTransport(handler)))
        with synthetic_client(provider) as client, patch.object(provider,'_call',side_effect=call):
            engine=client.app.state.session_factory.kw['bind']
            metadata=MetaData();metadata.reflect(engine)
            with engine.connect() as connection:
                before={name:connection.execute(select(table)).all() for name,table in metadata.tables.items()}
            response=client.post(f'/api/v2/investigation/incidents/{CASE_IDS["A"]}/ai-briefing',
                headers={'Authorization':'Bearer '+TOKEN},json={'schema_version':1})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(provider.preflight,{'status':'passed','input_tokens':1500})
            self.assertEqual(provider.generation['status'],'passed')
            self.assertEqual(len(requests),2)
            self.assertNotIn('test-key',response.text)
            allowed={source.citation for source in fixed_context('A').sources.values()}
            self.assertTrue(all(source['citation'] in allowed for source in response.json()['sources']))
            with engine.connect() as connection:
                for name,table in metadata.tables.items():
                    self.assertEqual(connection.execute(select(table)).all(),before[name],name)

    def test_failed_sdk_preflight_is_sanitized_and_consumes_usage(self):
        provider=SyntheticOpenAIProvider('A',SecretStr('test-key'))
        with synthetic_client(provider) as client, patch.object(provider,'_call',
                new=unittest.mock.AsyncMock(side_effect=ValueError('PRIVATE test-key'))) as call:
            url=f'/api/v2/investigation/incidents/{CASE_IDS["A"]}/ai-briefing'
            response=client.post(url,headers={'Authorization':'Bearer '+TOKEN},json={'schema_version':1})
            self.assertEqual(response.status_code,503)
            self.assertNotIn('PRIVATE',response.text);self.assertNotIn('test-key',response.text)
            self.assertEqual(provider.generation['status'],'not_attempted')
            self.assertEqual(client.app.state.ai_usage.attempts,1)
            retry=client.post(url,headers={'Authorization':'Bearer '+TOKEN},json={'schema_version':1})
            self.assertEqual(retry.status_code,429)
            self.assertEqual(call.await_count,1)

    def test_actual_endpoint_context_matches_fixed_fixtures_and_preserves_records(self):
        class Provider:
            def count_input_tokens(self, *, instructions, data):
                self.seen=data; return 100
            async def select_sources(self, **kwargs): return '{"sources":["S1"]}'
        provider=Provider()
        with synthetic_client(provider) as client:
            # No network; bypass admission only to compare every deterministic fixture quickly.
            with patch.object(client.app.state.ai_usage, 'admit'):
                for scenario,cid in CASE_IDS.items():
                    response=client.post(f'/api/v2/investigation/incidents/{cid}/ai-briefing',
                        headers={'Authorization':'Bearer '+TOKEN},json={'schema_version':1})
                    self.assertEqual(response.status_code,200,response.text)
                    self.assertEqual(provider.seen,fixed_context(scenario).data)
            with client.app.state.session_factory() as db:
                self.assertEqual(len(db.scalars(select(Incident)).all()),4)

    def test_auth_and_cross_owner_denial_do_not_reach_provider(self):
        provider=unittest.mock.Mock()
        with synthetic_client(provider) as client:
            url=f'/api/v2/investigation/incidents/{CASE_IDS["A"]}/ai-briefing'
            self.assertEqual(client.post(url,json={'schema_version':1}).status_code,401)
            with client.app.state.session_factory() as db:
                db.get(Incident,CASE_IDS['A']).created_by_id=OTHER_ACTOR; db.commit()
            self.assertEqual(client.post(url,headers={'Authorization':'Bearer '+TOKEN},
                                        json={'schema_version':1}).status_code,404)
            provider.count_input_tokens.assert_not_called()

    def test_normal_command_environment_cannot_opt_into_remote_preflight(self):
        from pathlib import Path
        script=Path(__file__).with_name('openai_synthetic_adapter.py').resolve()
        with patch.dict('os.environ',{'PHASE7J_SYNTHETIC_EVALUATION':'1','OPENAI_API_KEY':'test-key'}):
            provider=CommandProvider(script)
        self.assertNotIn('OPENAI_API_KEY',provider.environment)
        self.assertNotIn('PHASE7J_SYNTHETIC_EVALUATION',provider.environment)
        with self.assertRaises(ValueError):
            asyncio.run(provider.count_input_tokens(instructions=SYSTEM_INSTRUCTIONS,data=fixed_context('A').data))

    def test_parent_rejects_select_without_preflight_and_context_mismatch(self):
        provider=SyntheticOpenAIProvider('A',SecretStr('test-key'))
        with self.assertRaises(ValueError):
            asyncio.run(provider.select_sources(instructions=SYSTEM_INSTRUCTIONS,data=fixed_context('A').data,
                max_output_bytes=32768,max_output_tokens=1024))
        with self.assertRaises(ValueError):
            asyncio.run(provider.count_input_tokens(instructions=SYSTEM_INSTRUCTIONS,data='REAL PRIVATE DATA'))
        self.assertEqual(provider.preflight['status'],'failed_or_cancelled')

    def test_over_limit_preflight_never_generates(self):
        provider=SyntheticOpenAIProvider('A',SecretStr('test-key'))
        with patch.object(provider,'_call',new=unittest.mock.AsyncMock(return_value='{"input_tokens":8001}')) as call:
            with self.assertRaises(Exception):
                asyncio.run(BoundedCall(provider,fixed_context('A').data,30,8000,32768).run())
            self.assertEqual(call.await_count,1)
            self.assertEqual(provider.generation['status'],'not_attempted')

    def test_missing_config_and_preview_never_dispatch(self):
        out=io.StringIO()
        with patch('evaluate_openai.local_configuration',return_value=(None,MODEL)), \
                patch('evaluate_openai.SyntheticOpenAIProvider') as provider, redirect_stdout(out):
            self.assertEqual(main(['--run-approved-synthetic']),2)
            self.assertEqual(main([]),0)
            provider.assert_not_called()
        self.assertIn('Preflight calls: 0',out.getvalue())


if __name__=='__main__': unittest.main()
