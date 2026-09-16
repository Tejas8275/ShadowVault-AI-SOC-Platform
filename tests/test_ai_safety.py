import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from pydantic import SecretStr
from app.core.config import Settings
from app.main import create_app
from app.services.ai_adapter import CommandProvider
from app.services.ai_execution import BoundedCall
from app.services.ai_usage import UsageControl
from app.services import ai_context, ai_briefing
from synthetic_ai_cases import synthetic_case, ATTACKS
import test_ai_briefing


class ContextSafetyTests(unittest.TestCase):
    def test_source_and_field_limits_never_truncate(self):
        draft=synthetic_case()
        with patch.object(ai_context,'MAX_SOURCES',4):
            with self.assertRaises(HTTPException) as error:ai_context.build(draft)
            self.assertEqual(error.exception.status_code,413)
        with self.assertRaises(HTTPException):ai_context.build(synthetic_case(variant='large'))
        draft.case.description='X'*2048
        self.assertEqual(ai_context.build(draft).sources['S1'].fields['description'],draft.case.description)

    def test_synthetic_case_and_citation_isolation(self):
        a,b=[ai_context.build(synthetic_case(name)) for name in ('A','B')]
        self.assertNotIn('SYNTHETIC CASE B',a.data);self.assertNotIn('SYNTHETIC CASE A',b.data)
        self.assertNotEqual(ai_context.resolve(a,'{"sources":["S1"]}')[0].citation,
                            ai_context.resolve(b,'{"sources":["S1"]}')[0].citation)
        for sources in [['missing'],[a.sources['S1'].citation],['file:S1'],['S1','S1'],['S1']*21]:
            with self.subTest(sources=sources),self.assertRaises(ValueError):
                ai_context.resolve(b,json.dumps({'sources':sources}))

    def test_injection_is_data_and_never_output_instructions(self):
        context=ai_context.build(synthetic_case(variant='injection'))
        from app.services.ai_model import SYSTEM_INSTRUCTIONS
        for attack in ATTACKS:
            self.assertIn(attack,context.data);self.assertNotIn(attack,SYSTEM_INSTRUCTIONS)
        rows=ai_context.resolve(context,json.dumps({'sources':list(context.sources)}))
        self.assertEqual(len(rows),5)
        with self.assertRaises(ValueError):ai_context.resolve(context,'{"sources":["S1"],"verdict":"malicious"}')

    def test_empty_case_has_only_case_metadata(self):
        context=ai_context.build(synthetic_case(variant='empty'))
        self.assertEqual(list(context.sources),['S1'])


class UsageTests(unittest.TestCase):
    def test_cooldown_window_and_finite_budget(self):
        now=[0.0];budget=UsageControl(5,2,3,lambda:now[0])
        budget.admit()
        with self.assertRaises(HTTPException):budget.admit()
        now[0]=5;budget.admit();now[0]=10
        with self.assertRaises(HTTPException):budget.admit()
        now[0]=61;budget.admit();now[0]=200
        with self.assertRaises(HTTPException):budget.admit()
        self.assertEqual(budget.attempts,3)

    def test_concurrent_admission_is_atomic(self):
        budget=UsageControl(0,60,1)
        def attempt(_):
            try:budget.admit();return True
            except HTTPException:return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(attempt,range(20))),1)


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.script=Path(self.temp.name)/'adapter.py'
        self.processes=[]
        real=asyncio.create_subprocess_exec
        async def track(*args,**kwargs):
            p=await real(*args,**kwargs);self.processes.append(p);return p
        self.tracker=patch('asyncio.create_subprocess_exec',track);self.tracker.start()
    async def asyncTearDown(self):
        self.tracker.stop()
        self.assertTrue(all(p.returncode is not None for p in self.processes))
        self.temp.cleanup()
    def provider(self, body):
        self.script.write_text('import json,sys,time,os\nr=json.load(sys.stdin)\n'+body,encoding='utf-8')
        return CommandProvider(self.script,SecretStr('synthetic-provider-key'))
    async def call(self,provider,seconds=2):
        return await BoundedCall(provider,ai_context.build(synthetic_case()).data,seconds,8000,32768).run()
    async def test_command_contract_and_environment_minimization(self):
        provider=self.provider("assert sys.stdin.encoding.lower().replace('-','')=='utf8'\nassert 'SHADOWVAULT_OPERATOR_TOKEN_SHA256' not in os.environ\nassert 'synthetic-provider-key' not in json.dumps(r)\nprint(json.dumps({'input_tokens':100} if r['operation']=='count' else {'sources':['S1']}))")
        self.assertEqual(json.loads(await self.call(provider)),{'sources':['S1']})
        self.assertEqual(len(self.processes),2)
    async def test_count_timeout_kills_process_before_selection(self):
        provider=self.provider('time.sleep(30)')
        start=time.monotonic()
        with self.assertRaises(TimeoutError):await self.call(provider,0.15)
        self.assertLess(time.monotonic()-start,2)
        self.assertEqual(len(self.processes),1)
    async def test_select_timeout_and_no_retry(self):
        provider=self.provider("if r['operation']=='count':print('{\"input_tokens\":100}')\nelse:time.sleep(30)")
        with self.assertRaises(TimeoutError):await self.call(provider,0.5)
        self.assertEqual(len(self.processes),2)
    async def test_oversized_and_invalid_count_stop_before_selection(self):
        for body in ["print('X'*1000000)","print('{\"input_tokens\":8001}')","print('{\"input_tokens\":true}')",
                     "print('{\"input_tokens\":1,\"input_tokens\":2}')"]:
            with self.subTest(body=body):
                start=len(self.processes)
                with self.assertRaises((ValueError,HTTPException)):await self.call(self.provider(body))
                self.assertEqual(len(self.processes),start+1)
    async def test_output_size_is_bounded_while_reading(self):
        provider=self.provider("if r['operation']=='count':print('{\"input_tokens\":100}')\nelse:print('X'*1000000);time.sleep(30)")
        with self.assertRaises(ValueError):await self.call(provider)
    async def test_cancel_terminates_adapter(self):
        provider=self.provider('time.sleep(30)')
        task=asyncio.create_task(self.call(provider))
        for _ in range(100):
            if self.processes:break
            await asyncio.sleep(0.01)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task


class ApiSafetyTests(unittest.TestCase):
    setUp=test_ai_briefing.BriefingTests.setUp
    tearDown=test_ai_briefing.BriefingTests.tearDown
    briefing=test_ai_briefing.BriefingTests.briefing
    def test_usage_error_prevents_provider_and_consumes_failures(self):
        self.client.app.state.ai_usage=UsageControl(0,60,1)
        async def failure(**kwargs):raise ValueError('PRIVATE')
        self.provider.select_sources=failure
        self.assertEqual(self.briefing().status_code,503)
        self.assertEqual(self.briefing().status_code,429)
        self.assertEqual(self.client.app.state.ai_usage.attempts,1)
    def test_blocking_injected_count_times_out_without_dispatch(self):
        def slow(**kwargs):time.sleep(0.4);return 10
        self.provider.count_input_tokens=slow
        with patch.object(ai_briefing,'MAX_SECONDS',0.01):
            start=time.monotonic();self.assertEqual(self.briefing().status_code,504)
            self.assertLess(time.monotonic()-start,0.35)
        self.assertEqual(self.briefing().status_code,429)  # Quarantined, not another abandoned call.
        self.assertEqual(self.provider.inputs,[])
        time.sleep(0.45)
    def test_disabled_or_incomplete_configuration_stays_unconfigured(self):
        for settings in [Settings(_env_file=None),Settings(_env_file=None,ai_enabled=True)]:
            self.assertIsNone(create_app(settings).state.ai_provider)
        with self.assertRaises(ValueError):
            create_app(Settings(_env_file=None,ai_enabled=True,ai_adapter_script='relative.py'))
        with tempfile.TemporaryDirectory() as folder:
            script=Path(folder)/'reviewed.py';script.write_text('# no automatic invocation',encoding='utf-8')
            self.assertIsNone(create_app(Settings(_env_file=None,ai_adapter_script=script)).state.ai_provider)
            self.assertIsInstance(create_app(Settings(_env_file=None,ai_enabled=True,ai_adapter_script=script)).state.ai_provider,CommandProvider)
    def test_configured_key_in_metadata_is_blocked(self):
        from uuid import UUID
        from app.models import Incident
        self.client.app.state.settings.ai_provider_api_key=SecretStr('synthetic-"key')
        with self.factory() as db:
            db.get(Incident,UUID(self.id)).description='synthetic-"key';db.commit()
        self.assertEqual(self.briefing().status_code,422)
        self.assertEqual(self.provider.inputs,[])
