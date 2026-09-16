"""Gemini deterministic transport and endpoint tests. No live provider calls."""
import asyncio
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from pydantic import SecretStr
from sqlalchemy import MetaData, select
from app.models import Incident
from app.services.ai_adapter import CommandProvider
from app.services.ai_execution import BoundedCall
from app.services.ai_model import SYSTEM_INSTRUCTIONS
from gemini_synthetic_adapter import evaluate, MODEL, safe_failure, MAX_HTTP_BYTES
from evaluate_gemini import SyntheticGeminiProvider, synthetic_client, main
from openai_synthetic_data import fixed_context, SCENARIOS, CASE_IDS, TOKEN, OTHER_ACTOR


def request_for(operation='count', scenario='A'):
    value=dict(operation=operation,instructions=SYSTEM_INSTRUCTIONS,data=fixed_context(scenario).data)
    if operation=='select':value.update(max_output_bytes=32768,max_output_tokens=1024)
    return value


def generated(raw='{"sources":["S1","S2"]}'):
    return {'modelVersion':MODEL,'candidates':[{'finishReason':'STOP',
        'content':{'role':'model','parts':[{'text':raw}]}}],
        'usageMetadata':{'promptTokenCount':1400,'candidatesTokenCount':20,'totalTokenCount':1420}}


class GeminiTransportTests(unittest.TestCase):
    def test_opaque_signature_is_discarded_without_changing_selection(self):
        response = generated()
        response['candidates'][0]['content']['parts'][0]['thoughtSignature'] = 'OPAQUE-SYNTHETIC-SIGNATURE'
        result = evaluate(request_for('select'), 'A', 'TEST-SECRET',
                          transport=self.transport(response))
        self.assertEqual(json.loads(result['selection']), {'sources': ['S1', 'S2']})
        self.assertNotIn('OPAQUE-SYNTHETIC-SIGNATURE', json.dumps(result))

    def test_signature_does_not_allow_thoughts_tools_unknown_fields_or_bad_usage(self):
        for field, value in [('thought', True), ('functionCall', {}), ('unknown', 'data'),
                             ('thoughtSignature', {}), ('thoughtSignature', '')]:
            response = generated()
            part = response['candidates'][0]['content']['parts'][0]
            part['thoughtSignature'] = 'OPAQUE-SYNTHETIC-SIGNATURE'
            part[field] = value
            with self.assertRaises(ValueError):
                evaluate(request_for('select'), 'A', 'TEST-SECRET',
                         transport=self.transport(response))
        response = generated()
        response['candidates'][0]['content']['parts'][0]['thoughtSignature'] = 'OPAQUE-SYNTHETIC-SIGNATURE'
        response['usageMetadata']['thoughtsTokenCount'] = 1
        with self.assertRaises(ValueError):
            evaluate(request_for('select'), 'A', 'TEST-SECRET',
                     transport=self.transport(response))

    def test_supported_model_pin_and_retired_model_rejection(self):
        from evaluate_gemini import MODEL as runner_model
        self.assertEqual(MODEL, 'gemini-3.6-flash')
        self.assertEqual(runner_model, MODEL)
        evaluate(request_for(), 'A', 'TEST-SECRET',
                 transport=self.transport({'totalTokens': 1647}))
        self.assertEqual(str(self.calls[0].url),
                         'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:countTokens')
        self.assertEqual(json.loads(self.calls[0].content)['generateContentRequest']['model'],
                         'models/gemini-3.6-flash')
        with self.assertRaises(ValueError):
            evaluate(request_for(), 'A', 'TEST-SECRET', 'gemini-2.5-flash',
                     transport=self.transport({}))
        self.assertEqual(self.calls, [])

    def transport(self, result, status=200, headers=None):
        self.calls=[]
        def handler(request):
            self.calls.append(request)
            raw=result if isinstance(result,bytes) else json.dumps(result).encode()
            return httpx.Response(status,headers=headers or {},stream=httpx.ByteStream(raw))
        return httpx.MockTransport(handler)

    def test_count_and_generation_match_and_credentials_only_in_header(self):
        result=evaluate(request_for(),'A','TEST-SECRET',transport=self.transport({'totalTokens':1400}))
        self.assertEqual(result,{'input_tokens':1400})
        count=json.loads(self.calls[0].content)['generateContentRequest']
        self.assertTrue(str(self.calls[0].url).endswith(':countTokens'))
        result=evaluate(request_for('select'),'A','TEST-SECRET',transport=self.transport(generated()))
        self.assertEqual(json.loads(self.calls[0].content),count)
        self.assertNotIn('TEST-SECRET',self.calls[0].content.decode())
        self.assertNotIn('TEST-SECRET',str(self.calls[0].url))
        self.assertEqual(self.calls[0].headers['x-goog-api-key'],'TEST-SECRET')
        self.assertEqual(count['generationConfig']['maxOutputTokens'],1024)
        self.assertEqual(count['generationConfig']['thinkingConfig']['thinkingBudget'],0)
        self.assertNotIn('tools',count);self.assertNotIn('cachedContent',count)
        self.assertEqual(result['usage']['output_tokens'],20)
        self.assertEqual(len(self.calls),1)

    def test_untrusted_cross_case_and_changed_instructions_never_reach_transport(self):
        for field in ('data','instructions','extra'):
            payload=request_for();payload[field]='REAL PRIVATE DATA'
            with self.assertRaises(ValueError):evaluate(payload,'A','TEST-SECRET',transport=self.transport({}))
            self.assertEqual(self.calls,[])
        with self.assertRaises(ValueError):evaluate(request_for(scenario='B'),'A','TEST-SECRET',transport=self.transport({}))
        self.assertEqual(self.calls,[])

    def test_model_key_limits_and_operation_rejected_locally(self):
        for key,model in [('',MODEL),('TEST-SECRET','other'),('Synthetic',MODEL)]:
            with self.assertRaises(ValueError):evaluate(request_for(),'A',key,model,transport=self.transport({}))
            self.assertEqual(self.calls,[])
        for payload in [dict(request_for(),operation='other'),dict(request_for('select'),max_output_tokens=2000)]:
            with self.assertRaises(ValueError):evaluate(payload,'A','TEST-SECRET',transport=self.transport({}))
            self.assertEqual(self.calls,[])

    def test_invalid_counts_and_duplicate_json_fail(self):
        for result in [{'totalTokens':True},{'totalTokens':0},{'totalTokens':'9'},
                       b'{"totalTokens":1,"totalTokens":2}',b'not json']:
            with self.assertRaises(ValueError):evaluate(request_for(),'A','TEST-SECRET',transport=self.transport(result))

    def test_unknown_duplicate_cross_case_and_prose_selections_fail(self):
        for raw in ['oops','{"sources":["S999"]}','{"sources":["S1","S1"]}',
                    '{"sources":["S1"],"verdict":"malicious"}','{"sources":[]}',
                    '{"sources":["incident:00000000-0000-0000-0000-0000000007d0"]}']:
            with self.assertRaises(ValueError):evaluate(request_for('select'),'A','TEST-SECRET',transport=self.transport(generated(raw)))

    def test_refusal_tools_grounding_thoughts_and_excess_usage_fail(self):
        variants=[]
        x=generated();x['candidates'][0]['finishReason']='MAX_TOKENS';variants.append(x)
        x=generated();x['modelVersion']='other';variants.append(x)
        x=generated();x['candidates'][0]['content']['parts']=[{'functionCall':{}}];variants.append(x)
        x=generated();x['candidates'][0]['groundingMetadata']={'source':'external'};variants.append(x)
        x=generated();x['promptFeedback']={'blockReason':'SAFETY'};variants.append(x)
        x=generated();x['usageMetadata']['thoughtsTokenCount']=1;variants.append(x)
        x=generated();x['usageMetadata']['promptTokenCount']=8001;variants.append(x)
        x=generated();x['usageMetadata']['candidatesTokenCount']=1025;variants.append(x)
        for result in variants:
            with self.assertRaises(ValueError):evaluate(request_for('select'),'A','TEST-SECRET',transport=self.transport(result))

    def test_http_errors_sanitized_and_never_retried(self):
        for code in (400,401,429,500,503):
            with self.assertRaises(httpx.HTTPStatusError) as caught:
                evaluate(request_for(),'A','TEST-SECRET',transport=self.transport({'PRIVATE':'TEST-SECRET'},code))
            self.assertEqual(safe_failure(caught.exception),{'evaluation_error':'http_error','http_status':code})
            self.assertEqual(len(self.calls),1)
        self.assertEqual(safe_failure(ValueError('TEST-SECRET')),{'evaluation_error':'validation_rejected'})

    def test_transport_timeout_is_bounded_and_not_retried(self):
        calls=[]
        def handler(request):
            calls.append(request);raise httpx.ReadTimeout('PRIVATE')
        with self.assertRaises(httpx.ReadTimeout) as caught:
            evaluate(request_for(),'A','TEST-SECRET',transport=httpx.MockTransport(handler))
        self.assertEqual(safe_failure(caught.exception),{'evaluation_error':'timeout'})
        self.assertEqual(len(calls),1)

    def test_redirect_encoding_and_large_error_response_rejected(self):
        for result,status,headers in [(b'',302,{'location':'https://example.test'}),
                (b'x',200,{'content-encoding':'gzip'}),(b'',200,{'content-length':str(MAX_HTTP_BYTES+1)}),
                (b'x'*(MAX_HTTP_BYTES+1),500,{})]:
            with self.assertRaises(ValueError):evaluate(request_for(),'A','TEST-SECRET',transport=self.transport(result,status,headers))
            self.assertEqual(len(self.calls),1)


class GeminiBoundaryTests(unittest.TestCase):
    def test_normal_provider_cannot_enable_gemini_or_inherit_credentials(self):
        path=Path(__file__).with_name('gemini_synthetic_adapter.py').resolve()
        with patch.dict('os.environ',{'GEMINI_API_KEY':'TEST-SECRET','OPENAI_API_KEY':'OTHER',
                                    'PHASE7JG_SYNTHETIC_EVALUATION':'1'}):
            provider=CommandProvider(path)
            gemini=SyntheticGeminiProvider('A',SecretStr('TEST-SECRET'))
        self.assertNotIn('OPENAI_API_KEY',gemini.environment)
        self.assertNotIn('GEMINI_API_KEY',provider.environment)
        self.assertNotIn('PHASE7JG_SYNTHETIC_EVALUATION',provider.environment)
        with self.assertRaises(ValueError):asyncio.run(provider.count_input_tokens(
            instructions=SYSTEM_INSTRUCTIONS,data=fixed_context('A').data))

    def test_direct_selection_and_non_synthetic_child_input_rejected(self):
        provider=SyntheticGeminiProvider('A',SecretStr('TEST-SECRET'))
        with self.assertRaises(ValueError):asyncio.run(provider.select_sources(
            instructions=SYSTEM_INSTRUCTIONS,data=fixed_context('A').data,max_output_bytes=32768,max_output_tokens=1024))
        with self.assertRaises(ValueError):asyncio.run(provider.count_input_tokens(
            instructions=SYSTEM_INSTRUCTIONS,data='REAL PRIVATE DATA'))
        self.assertEqual(provider.preflight['evaluation_error'],'validation_rejected')

    def test_preflight_over_limit_never_generates(self):
        provider=SyntheticGeminiProvider('A',SecretStr('TEST-SECRET'))
        with patch.object(provider,'_call',new=AsyncMock(return_value='{"input_tokens":8001}')) as call:
            with self.assertRaises(Exception):asyncio.run(BoundedCall(provider,fixed_context('A').data,30,8000,32768).run())
            self.assertEqual(call.await_count,1);self.assertEqual(provider.generation['status'],'not_attempted')

    def test_endpoint_generation_preserves_records_and_server_citations(self):
        provider=SyntheticGeminiProvider('A',SecretStr('TEST-SECRET'))
        calls=[]
        async def call(operation,instructions,data,limit,**options):
            def handler(request):
                calls.append(request)
                result={'totalTokens':1400} if operation=='count' else generated()
                return httpx.Response(200,stream=httpx.ByteStream(json.dumps(result).encode()))
            return json.dumps(evaluate(dict(operation=operation,instructions=instructions,data=data,**options),
                'A','TEST-SECRET',transport=httpx.MockTransport(handler)))
        with synthetic_client(provider) as client,patch.object(provider,'_call',side_effect=call):
            engine=client.app.state.session_factory.kw['bind']
            metadata=MetaData();metadata.reflect(engine)
            with engine.connect() as db:before={n:db.execute(select(t)).all() for n,t in metadata.tables.items()}
            response=client.post(f'/api/v2/investigation/incidents/{CASE_IDS["A"]}/ai-briefing',
                headers={'Authorization':'Bearer '+TOKEN},json={'schema_version':1})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(len(calls),2);self.assertNotIn('TEST-SECRET',response.text)
            allowed={s.citation:s.model_dump(mode='json') for s in fixed_context('A').sources.values()}
            self.assertTrue(all(s==allowed.get(s['citation']) for s in response.json()['sources']))
            with engine.connect() as db:
                for n,t in metadata.tables.items():self.assertEqual(db.execute(select(t)).all(),before[n])

    def test_auth_and_other_owner_never_dispatch(self):
        provider=SyntheticGeminiProvider('A',SecretStr('TEST-SECRET'))
        with synthetic_client(provider) as client,patch.object(provider,'_call',new=AsyncMock()) as call:
            url=f'/api/v2/investigation/incidents/{CASE_IDS["A"]}/ai-briefing'
            self.assertEqual(client.post(url,json={'schema_version':1}).status_code,401)
            with client.app.state.session_factory() as db:
                db.get(Incident,CASE_IDS['A']).created_by_id=OTHER_ACTOR;db.commit()
            self.assertEqual(client.post(url,headers={'Authorization':'Bearer '+TOKEN},json={'schema_version':1}).status_code,404)
            call.assert_not_called()

    def test_failed_preflight_consumes_attempt_and_does_not_auto_retry(self):
        provider=SyntheticGeminiProvider('A',SecretStr('TEST-SECRET'))
        with synthetic_client(provider) as client,patch.object(provider,'_call',new=AsyncMock(side_effect=ValueError('PRIVATE'))) as call:
            url=f'/api/v2/investigation/incidents/{CASE_IDS["A"]}/ai-briefing'
            response=client.post(url,headers={'Authorization':'Bearer '+TOKEN},json={'schema_version':1})
            self.assertEqual(response.status_code,503);self.assertNotIn('PRIVATE',response.text)
            self.assertEqual(client.app.state.ai_usage.attempts,1)
            self.assertEqual(client.post(url,headers={'Authorization':'Bearer '+TOKEN},json={'schema_version':1}).status_code,429)
            self.assertEqual(call.await_count,1)

    def test_preview_missing_key_and_wrong_model_never_dispatch(self):
        with redirect_stdout(io.StringIO()) as output,patch('evaluate_gemini.SyntheticGeminiProvider') as provider:
            self.assertEqual(main([]),0)
            with patch('evaluate_gemini.local_configuration',return_value=(None,MODEL)):
                self.assertEqual(main(['--run-approved-synthetic']),2)
            with patch('evaluate_gemini.local_configuration',return_value=(SecretStr('TEST-SECRET'),'other')):
                self.assertEqual(main(['--run-approved-synthetic']),2)
            provider.assert_not_called()
        self.assertNotIn('TEST-SECRET',output.getvalue())


if __name__=='__main__':unittest.main()
