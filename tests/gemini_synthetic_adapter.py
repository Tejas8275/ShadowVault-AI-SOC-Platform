"""Phase 7J-G only. Fixed synthetic metadata; never a production adapter."""
import json
import logging
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'tests'))

import httpx
from openai_synthetic_data import fixed_context, SCENARIOS
from app.services.ai_model import SYSTEM_INSTRUCTIONS
from app.services.ai_context import resolve

MODEL = 'gemini-3.6-flash'
BASE = 'https://generativelanguage.googleapis.com/v1beta/models/' + MODEL
MAX_HTTP_BYTES = 65536
FAILURE_CODES = frozenset({'http_error', 'timeout', 'connection_error', 'validation_rejected', 'adapter_failure'})


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate field')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def safe_failure(error):
    if isinstance(error, httpx.HTTPStatusError):
        return {'evaluation_error': 'http_error', 'http_status': error.response.status_code}
    if isinstance(error, httpx.TimeoutException):
        return {'evaluation_error': 'timeout'}
    if isinstance(error, httpx.TransportError):
        return {'evaluation_error': 'connection_error'}
    return {'evaluation_error': 'validation_rejected' if isinstance(error, ValueError) else 'adapter_failure'}


def evaluate(request, scenario, key, model=MODEL, *, transport=None):
    if not key or model != MODEL or scenario not in SCENARIOS:
        raise ValueError('Unconfigured evaluation')
    context = fixed_context(scenario)
    operation = request.get('operation')
    fields = {'operation', 'instructions', 'data'}
    if operation == 'select':
        fields |= {'max_output_bytes', 'max_output_tokens'}
        if request.get('max_output_bytes') != 32768 or request.get('max_output_tokens') != 1024:
            raise ValueError('Invalid limits')
    elif operation != 'count':
        raise ValueError('Invalid operation')
    if (set(request) != fields or request['data'] != context.data
            or request['instructions'] != SYSTEM_INSTRUCTIONS or key in context.data):
        raise ValueError('Synthetic context mismatch')
    schema = {'type': 'object', 'properties': {'sources': {'type': 'array',
        'items': {'type': 'string', 'enum': list(context.sources)}, 'minItems': 1, 'maxItems': 20}},
        'required': ['sources'], 'additionalProperties': False}
    generation = {'model': 'models/' + MODEL,
        'systemInstruction': {'parts': [{'text': SYSTEM_INSTRUCTIONS}]},
        'contents': [{'role': 'user', 'parts': [{'text': context.data}]}],
        'generationConfig': {'candidateCount': 1, 'maxOutputTokens': 1024,
            'responseMimeType': 'application/json', 'responseJsonSchema': schema,
            'thinkingConfig': {'thinkingBudget': 0, 'includeThoughts': False}}}
    payload = {'generateContentRequest': generation} if operation == 'count' else generation
    endpoint = BASE + (':countTokens' if operation == 'count' else ':generateContent')
    # No automatic retries, proxy inheritance, redirects, tools, file APIs or URL key.
    inner = transport if transport is not None else httpx.HTTPTransport(verify=True, trust_env=False, retries=0)
    with httpx.Client(transport=inner, trust_env=False, follow_redirects=False,
                      timeout=httpx.Timeout(20, connect=5)) as client:
        with client.stream('POST', endpoint, json=payload,
                headers={'x-goog-api-key': key, 'Accept-Encoding': 'identity'}) as response:
            if response.headers.get('content-encoding', 'identity').lower() != 'identity':
                raise ValueError('Encoded response')
            if int(response.headers.get('content-length', '0')) > MAX_HTTP_BYTES:
                raise ValueError('Large response')
            raw = bytearray()
            for chunk in response.iter_raw(chunk_size=4096):
                raw.extend(chunk)
                if len(raw) > MAX_HTTP_BYTES:
                    raise ValueError('Large response')
            if 300 <= response.status_code < 400:
                raise ValueError('Redirect rejected')
            response.raise_for_status()
            result = strict_json(bytes(raw))
    if not isinstance(result, dict) or 'error' in result:
        raise ValueError('Invalid response')
    if operation == 'count':
        count = result.get('totalTokens')
        if type(count) is not int or count < 1:
            raise ValueError('Invalid count')
        return {'input_tokens': count}
    if result.get('modelVersion') != MODEL or result.get('promptFeedback', {}).get('blockReason'):
        raise ValueError('Unapproved or blocked response')
    candidates = result.get('candidates')
    if not isinstance(candidates, list) or len(candidates) != 1:
        raise ValueError('Unexpected candidates')
    candidate = candidates[0]
    if (candidate.get('finishReason') != 'STOP' or candidate.get('groundingMetadata')
            or candidate.get('citationMetadata') or candidate.get('urlContextMetadata')):
        raise ValueError('Incomplete or externally grounded output')
    content = candidate.get('content', {})
    parts = content.get('parts')
    if (content.get('role') != 'model' or not isinstance(parts, list) or len(parts) != 1
            or not isinstance(parts[0], dict) or 'text' not in parts[0]
            or not set(parts[0]) <= {'text', 'thoughtSignature'}):
        raise ValueError('Non-text output')
    # Gemini 3 can attach opaque signatures even to non-thinking text responses.
    # This single-turn evaluator discards them; they are never returned or reused.
    if ('thoughtSignature' in parts[0]
            and (not isinstance(parts[0]['thoughtSignature'], str) or not parts[0]['thoughtSignature'])):
        raise ValueError('Invalid signature metadata')
    selection = parts[0]['text']
    resolve(context, selection)
    usage = result.get('usageMetadata', {})
    counts = {'input_tokens': usage.get('promptTokenCount'),
              'output_tokens': usage.get('candidatesTokenCount'), 'total_tokens': usage.get('totalTokenCount')}
    if (any(type(v) is not int or v < 0 for v in counts.values()) or counts['input_tokens'] > 8000
            or counts['output_tokens'] > 1024 or counts['total_tokens'] != counts['input_tokens'] + counts['output_tokens']
            or usage.get('thoughtsTokenCount', 0) != 0 or usage.get('toolUsePromptTokenCount', 0) != 0):
        raise ValueError('Invalid usage')
    return {'selection': selection, 'usage': counts}


def main():
    logging.disable(logging.CRITICAL)
    try:
        if os.environ.get('PHASE7JG_SYNTHETIC_EVALUATION') != '1':
            raise ValueError('Explicit synthetic opt-in required')
        raw = sys.stdin.buffer.read(72 * 1024 + 1)
        if len(raw) > 72 * 1024:
            raise ValueError('Large input')
        result = evaluate(strict_json(raw), os.environ.get('PHASE7JG_SCENARIO'),
                          os.environ.get('GEMINI_API_KEY'), os.environ.get('GEMINI_MODEL'))
        output = json.dumps(result, ensure_ascii=False)
        if len(output.encode('utf-8')) > 32768:
            raise ValueError('Large output')
        sys.stdout.write(output)
    except Exception as error:
        sys.stdout.write(json.dumps(safe_failure(error)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
