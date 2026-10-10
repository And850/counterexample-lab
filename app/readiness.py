"""Explicit local inference smoke check; never called by ordinary tests or polling."""
import argparse
import json
import os
import time
import urllib.request
from urllib.parse import urlsplit

from dotenv import load_dotenv

from app.runner import readiness


def validate_smoke(response: dict) -> str:
    try:
        choice = response['choices'][0]
        if choice['finish_reason'] != 'stop':
            raise ValueError('Generation did not finish')
        message = choice['message']
        field = 'content' if message.get('content', '').strip() else 'reasoning_content'
        answer = json.loads(message[field])
        if not isinstance(answer, dict) or set(answer) != {'status', 'sum'}:
            raise ValueError('Unexpected JSON fields')
        if answer['status'] != 'ok' or type(answer['sum']) is not int or answer['sum'] != 5:
            raise ValueError('Incorrect smoke answer')
        return field
    except (KeyError, IndexError, TypeError, AttributeError) as error:
        raise ValueError('Malformed smoke response') from error


def local_smoke() -> dict:
    base = os.getenv('LMSTUDIO_BASE_URL', 'http://127.0.0.1:1234/v1').rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('LM Studio must use a loopback HTTP endpoint')
    model = os.getenv('LMSTUDIO_MODEL', 'counterexample-local')
    schema = {
        'type': 'object',
        'properties': {'status': {'type': 'string'}, 'sum': {'type': 'integer'}},
        'required': ['status', 'sum'], 'additionalProperties': False,
    }
    body = {
        'model': model,
        'messages': [{'role': 'user', 'content': 'Return status ok and the integer sum of 2 and 3.'}],
        'temperature': 0, 'max_tokens': 256,
        'response_format': {'type': 'json_schema', 'json_schema': {'name': 'smoke', 'strict': True, 'schema': schema}},
    }
    request = urllib.request.Request(base + '/chat/completions', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    start = time.monotonic()
    with urllib.request.urlopen(request, timeout=45) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Model response exceeds limit')
    field = validate_smoke(json.loads(raw))
    return {
        'ready': True, 'name': 'lmstudio', 'model': model,
        'elapsed': round(time.monotonic() - start, 2), 'response_field': field,
        'compatibility_required': field != 'content',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Run one local schema-constrained inference request')
    options = parser.parse_args()
    load_dotenv()
    result = {'runner': readiness()}
    if options.live:
        if os.getenv('MODEL_PROVIDER', 'lmstudio') != 'lmstudio':
            result['provider'] = {'ready': False, 'error': 'This prerequisite smoke command tests LM Studio. Gemini generation remains unverified.'}
        else:
            try:
                result['provider'] = local_smoke()
            except Exception:
                # Do not print raw request errors or any environment credentials.
                result['provider'] = {'ready': False, 'error': 'Local inference failed, timed out, or returned invalid JSON.'}
    print(json.dumps(result, indent=2))
    return 0 if all(value.get('ready', False) for value in result.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
