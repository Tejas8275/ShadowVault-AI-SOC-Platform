"""Opt-in loopback browser evaluation of the existing fixed synthetic fixtures."""
import argparse
from contextlib import asynccontextmanager
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from starlette.responses import JSONResponse
from app.core.config import Settings
from app.main import create_app
from app.services.ai_adapter import CommandProvider
from app.services.ai_model import SYSTEM_INSTRUCTIONS
from evaluate_gemini import SyntheticGeminiProvider, local_configuration, MODEL
from openai_synthetic_data import settings, seed, fixed_context, SCENARIOS, CASE_IDS


class BrowserEvaluationProvider(CommandProvider):
    """Normal provider is untouched; every remote input must equal a fixed fixture."""
    def __init__(self, key, model=MODEL):
        self.key, self.model = key, model
        self.contexts = {fixed_context(name).data: name for name in SCENARIOS}
        self.current = None
        self.current_data = None

    async def count_input_tokens(self, *, instructions, data):
        self.current = self.current_data = None
        if instructions != SYSTEM_INSTRUCTIONS or data not in self.contexts:
            raise ValueError('Only fixed synthetic fixtures are permitted')
        self.current = SyntheticGeminiProvider(self.contexts[data], self.key, self.model)
        self.current_data = data
        return await self.current.count_input_tokens(instructions=instructions, data=data)

    async def select_sources(self, *, instructions, data, max_output_bytes, max_output_tokens):
        if self.current is None or instructions != SYSTEM_INSTRUCTIONS or data != self.current_data:
            raise ValueError('Matching synthetic preflight required')
        provider, self.current = self.current, None
        self.current_data = None
        return await provider.select_sources(instructions=instructions, data=data,
            max_output_bytes=max_output_bytes, max_output_tokens=max_output_tokens)


class ReadOnlyDemo:
    def __init__(self, app):
        self.app = app
        self.allowed = {f'/api/v2/investigation/incidents/{cid}/ai-briefing' for cid in CASE_IDS.values()}

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            method, path = scope['method'], scope['path']
            if method not in {'GET', 'HEAD', 'OPTIONS'} and not (method == 'POST' and path in self.allowed):
                return await JSONResponse({'detail': 'Synthetic browser demo is read-only; only AI briefing is enabled'},
                    status_code=403, headers={'Cache-Control': 'no-store'})(scope, receive, send)
        await self.app(scope, receive, send)


def demo_app(operator_digest, provider, provider_key=None):
    if not operator_digest:
        raise ValueError('Configured operator required')
    config = settings()  # Explicit in-memory SQLite; never load a disk database.
    config.operator_token_sha256 = operator_digest
    config.ai_provider_api_key = provider_key
    config.cors_origins = ['http://127.0.0.1:5180']
    config.app_name = 'ShadowVault — fixed synthetic Gemini evaluation'
    app = create_app(config, ai_provider=provider)
    normal_lifespan = app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(application):
        async with normal_lifespan(application):
            seed(application.state.session_factory.kw['bind'])
            yield
    app.router.lifespan_context = lifespan
    app.add_middleware(ReadOnlyDemo)
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-approved-synthetic', action='store_true', required=True)
    parser.parse_args()
    key, model = local_configuration()
    config = Settings()
    if key is None or model != MODEL or config.operator_token_sha256 is None:
        print('Demo not started: configure the approved Gemini model/key and existing operator digest privately.')
        return 2
    import uvicorn
    print('Synthetic-only demo API: http://127.0.0.1:8010; frontend must use port 5180. No data survives shutdown.')
    uvicorn.run(demo_app(config.operator_token_sha256, BrowserEvaluationProvider(key, model), key),
        host='127.0.0.1', port=8010, access_log=False, proxy_headers=False,
        log_config=str(ROOT / 'backend' / 'logging.json'))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('Synthetic demo stopped. Check private configuration and port availability; no details logged.')
        raise SystemExit(1)
