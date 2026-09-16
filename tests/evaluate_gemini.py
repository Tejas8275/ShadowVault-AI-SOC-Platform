"""Explicit Phase 7J-G synthetic-only endpoint evaluation; no production configuration wiring."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from fastapi.testclient import TestClient
from pydantic import SecretStr
from app.main import create_app
from app.services.ai_adapter import CommandProvider
from app.services.ai_context import resolve
from openai_synthetic_data import settings, seed, fixed_context, CASE_IDS, SCENARIOS, TOKEN

MODEL = 'gemini-3.6-flash'


class SyntheticGeminiProvider(CommandProvider):
    """Test-only override. Normal CommandProvider counting remains local-only."""
    def __init__(self, scenario, key, model=MODEL):
        if scenario not in SCENARIOS or not key or model != MODEL:
            raise ValueError('Synthetic configuration invalid')
        super().__init__(Path(__file__).with_name('gemini_synthetic_adapter.py').resolve())
        self.environment.update(PHASE7JG_SYNTHETIC_EVALUATION='1', PHASE7JG_SCENARIO=scenario,
                                GEMINI_API_KEY=key.get_secret_value(), GEMINI_MODEL=model)
        self.scenario = scenario
        self.preflight = {'status': 'not_attempted'}
        self.generation = {'status': 'not_attempted'}
        self.failure = {}

    async def _call(self, *args, **kwargs):
        raw = await super()._call(*args, **kwargs)
        value = json.loads(raw)
        if isinstance(value, dict) and 'evaluation_error' in value:
            from gemini_synthetic_adapter import FAILURE_CODES
            if (set(value) <= {'evaluation_error', 'http_status'}
                    and value['evaluation_error'] in FAILURE_CODES
                    and ('http_status' not in value or type(value['http_status']) is int
                         and 400 <= value['http_status'] <= 599)):
                self.failure = value
            raise ValueError('Synthetic adapter rejected operation')
        return raw

    async def count_input_tokens(self, *, instructions, data):
        if self.preflight['status'] != 'not_attempted':
            raise ValueError('New explicit evaluation attempt required')
        self.preflight = {'status': 'attempted'}
        try:
            count = await super().count_input_tokens(instructions=instructions, data=data)
            self.preflight = {'status': 'passed' if count <= 8000 else 'over_limit', 'input_tokens': count}
            return count
        except BaseException:
            self.preflight = {'status': 'failed_or_cancelled', **self.failure}
            raise

    async def select_sources(self, *, instructions, data, max_output_bytes, max_output_tokens):
        # Prevent bypass through direct selection outside the bounded endpoint path.
        if self.preflight.get('status') != 'passed' or self.generation['status'] != 'not_attempted':
            raise ValueError('Preflight required; no automatic retry')
        self.generation = {'status': 'attempted'}
        try:
            raw = await self._call('select', instructions, data, max_output_bytes,
                                  max_output_bytes=max_output_bytes, max_output_tokens=max_output_tokens)
            result = json.loads(raw)
            if set(result) != {'selection', 'usage'}:
                raise ValueError('Invalid adapter output')
            resolve(fixed_context(self.scenario), result['selection'])
            self.generation = {'status': 'passed', 'usage': result['usage']}
            return result['selection']
        except BaseException:
            self.generation = {'status': 'failed_or_cancelled', **self.failure}
            raise


@contextmanager
def synthetic_client(provider=None):
    app = create_app(settings(), ai_provider=provider)
    with TestClient(app) as client:
        seed(app.state.session_factory.kw['bind'])
        yield client


def local_configuration():
    # Values are consumed only by backend test processes; never output or inspected in chat.
    from dotenv import dotenv_values
    local = dotenv_values(ROOT / 'backend' / '.env')
    key = os.environ.get('GEMINI_API_KEY') or local.get('GEMINI_API_KEY')
    model = os.environ.get('GEMINI_MODEL') or local.get('GEMINI_MODEL') or MODEL
    return SecretStr(key) if key else None, model


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-approved-synthetic', action='store_true')
    args = parser.parse_args(argv)
    if not args.run_approved_synthetic:
        print('PREVIEW: four fixed synthetic scenarios; no provider or network invoked.')
        for name in SCENARIOS:
            context = fixed_context(name)
            print(json.dumps({'scenario': name, 'source_count': len(context.sources),
                              'context_bytes': len(context.data.encode('utf-8'))}))
        return 0
    key, model = local_configuration()
    if not key:
        print('NOT RUN: GEMINI_API_KEY is not locally configured. Preflight calls: 0. Generation calls: 0.')
        return 2
    if model != MODEL:
        print('NOT RUN: only the approved model is permitted.')
        return 2
    # Four intentional attempts, no retry. Existing process-local cooldown/window/budget remain active.
    with synthetic_client() as client:
        for index, scenario in enumerate(SCENARIOS):
            if index:
                time.sleep(5)
            provider = SyntheticGeminiProvider(scenario, key, model)
            client.app.state.ai_provider = provider
            client.app.state.settings.ai_provider_api_key = key
            started = time.monotonic()
            response = client.post(f'/api/v2/investigation/incidents/{CASE_IDS[scenario]}/ai-briefing',
                                   headers={'Authorization': 'Bearer ' + TOKEN}, json={'schema_version': 1})
            valid = response.status_code == 200
            if valid:
                data = response.json()
                context = fixed_context(scenario)
                allowed = {row.citation: row.model_dump(mode='json') for row in context.sources.values()}
                valid = (data['case_id'] == str(CASE_IDS[scenario]) and bool(data['sources'])
                         and all(source == allowed.get(source['citation']) for source in data['sources']))
            print(json.dumps({'scenario': scenario, 'preflight': provider.preflight,
                'generation': provider.generation, 'endpoint_status': response.status_code,
                'server_grounding_and_case_isolation': 'passed' if valid else 'failed',
                'seconds': round(time.monotonic() - started, 3)}), flush=True)
            if not valid:
                print('STOPPED: evaluation failed; no automatic retry. No raw provider output published.')
                return 1
    print('Structural evaluation passed. Selection relevance and omission still require investigator review.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('Evaluation stopped safely; no private exception details published.')
        raise SystemExit(1)
