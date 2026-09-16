"""Phase 7J ONLY. Accepts exact reconstructed synthetic fixtures, never arbitrary context.

Not a production provider: the remote-count exception is confined to this test tool.
The parent uses the existing killable CommandProvider and total 30-second deadline.
"""
import json
import logging
import os
from pathlib import Path
import sys

# -I excludes environment/user import paths. Only repository-owned test/backend paths.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'tests'))

import httpx2
from openai import OpenAI, APIStatusError, APITimeoutError, APIConnectionError
from openai_synthetic_data import fixed_context, SCENARIOS
from app.services.ai_context import resolve
from app.services.ai_model import SYSTEM_INSTRUCTIONS

MODEL = 'gpt-5.6-terra'
MAX_HTTP_BYTES = 64 * 1024
FAILURE_CODES = frozenset({'http_error', 'timeout', 'connection_error', 'validation_rejected',
                           'incomplete_response', 'unexpected_output', 'unexpected_content',
                           'invalid_usage', 'adapter_failure'})


def safe_failure(error):
    """Never serialize an exception, response body, URL or headers."""
    if isinstance(error, APIStatusError):
        return {'evaluation_error': 'http_error', 'http_status': error.status_code}
    if isinstance(error, APITimeoutError):
        return {'evaluation_error': 'timeout'}
    if isinstance(error, APIConnectionError):
        return {'evaluation_error': 'connection_error'}
    if isinstance(error, ValueError):
        # Equality against fixed messages only. Unknown values are never published.
        codes = {'Incomplete response': 'incomplete_response', 'Unexpected output': 'unexpected_output',
                 'Unexpected content': 'unexpected_content', 'Invalid usage': 'invalid_usage'}
        return {'evaluation_error': codes.get(error.args[0] if error.args and isinstance(error.args[0], str)
                                              else '', 'validation_rejected')}
    return {'evaluation_error': 'adapter_failure'}


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate field')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


class BoundedTransport(httpx2.BaseTransport):
    """Bound both successful and error bodies before SDK parsing/error handling."""
    def __init__(self, inner, operation):
        self.inner = inner
        self.path = '/v1/responses/input_tokens' if operation == 'count' else '/v1/responses'
        self.used = False

    def handle_request(self, request):
        if self.used or str(request.url) != 'https://api.openai.com' + self.path or request.method != 'POST':
            raise ValueError('Unapproved request')
        self.used = True
        response = self.inner.handle_request(request)
        try:
            if response.headers.get('content-encoding', 'identity').lower() != 'identity':
                raise ValueError('Encoded response rejected')
            if int(response.headers.get('content-length', '0')) > MAX_HTTP_BYTES:
                raise ValueError('Response exceeds limit')
            content = bytearray()
            for chunk in response.iter_raw(chunk_size=4096):
                content.extend(chunk)
                if len(content) > MAX_HTTP_BYTES:
                    raise ValueError('Response exceeds limit')
            if 300 <= response.status_code < 400:
                raise ValueError('Redirect rejected')
            return httpx2.Response(response.status_code, headers=response.headers,
                                  content=bytes(content), request=request)
        finally:
            response.close()

    def close(self):
        self.inner.close()


def evaluate(request, scenario, key, model=MODEL, *, transport=None):
    """Network inputs always come from fixed_context, not request fields.

    transport is an in-process test seam only, never a CLI/environment option.
    """
    if not key or model != MODEL or scenario not in SCENARIOS:
        raise ValueError('Evaluation not configured')
    context = fixed_context(scenario)
    operation = request.get('operation')
    expected = {'operation', 'instructions', 'data'}
    if operation == 'select':
        expected |= {'max_output_bytes', 'max_output_tokens'}
        if request.get('max_output_bytes') != 32768 or request.get('max_output_tokens') != 1024:
            raise ValueError('Limits differ')
    elif operation != 'count':
        raise ValueError('Unknown operation')
    if (set(request) != expected or request['data'] != context.data
            or request['instructions'] != SYSTEM_INSTRUCTIONS or key in context.data):
        raise ValueError('Non-synthetic context rejected')
    schema = {'type': 'object', 'properties': {'sources': {'type': 'array',
        'items': {'type': 'string', 'enum': list(context.sources)}, 'minItems': 1, 'maxItems': 20}},
        'required': ['sources'], 'additionalProperties': False}
    common = dict(model=MODEL, instructions=SYSTEM_INSTRUCTIONS,
        input=[{'role': 'user', 'content': context.data}], reasoning={'effort': 'none'},
        text={'format': {'type': 'json_schema', 'name': 'source_selection', 'strict': True, 'schema': schema}},
        tools=[], tool_choice='none', parallel_tool_calls=False, truncation='disabled')
    inner = transport if transport is not None else httpx2.HTTPTransport(
        verify=True, trust_env=False, retries=0)
    with httpx2.Client(transport=BoundedTransport(inner, operation), trust_env=False,
                      follow_redirects=False, headers={'Accept-Encoding': 'identity'},
                      timeout=httpx2.Timeout(20, connect=5)) as http:
        with OpenAI(api_key=key, base_url='https://api.openai.com/v1', http_client=http,
                    max_retries=0, timeout=httpx2.Timeout(20, connect=5)) as client:
            if operation == 'count':
                with client.responses.input_tokens.with_streaming_response.count(**common) as response:
                    result = strict_json(response.read())
                if (not isinstance(result, dict) or set(result) != {'object', 'input_tokens'}
                        or result['object'] != 'response.input_tokens'
                        or type(result['input_tokens']) is not int or result['input_tokens'] < 1):
                    raise ValueError('Invalid count')
                return {'input_tokens': result['input_tokens']}
            with client.responses.with_streaming_response.create(**common, max_output_tokens=1024,
                    store=False, background=False, stream=False) as response:
                result = strict_json(response.read())
    if (result.get('status') != 'completed' or result.get('model') != MODEL
            or result.get('error') or result.get('incomplete_details')):
        raise ValueError('Incomplete response')
    output = result.get('output')
    if (not isinstance(output, list) or len(output) != 1 or output[0].get('type') != 'message'
            or output[0].get('role') != 'assistant' or output[0].get('status') != 'completed'):
        raise ValueError('Unexpected output')
    content = output[0].get('content')
    if (not isinstance(content, list) or len(content) != 1 or content[0].get('type') != 'output_text'
            or content[0].get('annotations')):
        raise ValueError('Unexpected content')
    raw = content[0].get('text')
    resolve(context, raw)  # Server will independently validate/resolve again.
    usage = result.get('usage', {})
    counts = {k: usage.get(k) for k in ('input_tokens', 'output_tokens', 'total_tokens')}
    if (any(type(v) is not int or v < 0 for v in counts.values())
            or counts['input_tokens'] > 8000 or counts['output_tokens'] > 1024
            or counts['total_tokens'] != counts['input_tokens'] + counts['output_tokens']):
        raise ValueError('Invalid usage')
    return {'selection': raw, 'usage': counts}


def main():
    logging.disable(logging.CRITICAL)
    try:
        if os.environ.get('PHASE7J_SYNTHETIC_EVALUATION') != '1':
            raise ValueError('Synthetic opt-in required')
        raw = sys.stdin.buffer.read(72 * 1024 + 1)
        if len(raw) > 72 * 1024:
            raise ValueError('Input exceeds limit')
        result = evaluate(strict_json(raw), os.environ.get('PHASE7J_SCENARIO'),
            os.environ.get('OPENAI_API_KEY'), os.environ.get('OPENAI_MODEL'))
        output = json.dumps(result, ensure_ascii=False)
        if len(output.encode('utf-8')) > 32768:
            raise ValueError('Output exceeds limit')
        sys.stdout.write(output)
        return 0
    except Exception as error:
        # Never print SDK errors, URLs, headers, credentials, prompts or raw output.
        sys.stdout.write(json.dumps(safe_failure(error)))
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
