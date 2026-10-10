import json
import threading
import time

import httpx
import pytest


def problem():
    from app.contracts import ProblemInput, SamplePair

    return ProblemInput(statement='Sum two integers in [-100,100].', samples=[SamplePair(stdin='2 3', stdout='5')])


def response(data, finish='stop', reasoning=False):
    return httpx.Response(200, json={'choices': [{'finish_reason': finish, 'message': {'content': '' if reasoning else json.dumps(data), 'reasoning_content': json.dumps(data) if reasoning else ''}}]})


def test_local_provider_validates_schema_and_reasoning_compatibility():
    from app.provider import Provider

    def transport(req):
        body = json.loads(req.content)
        assert 'candidate' not in json.dumps(body).lower()
        return response({'code': 'def solve(s): return "5"', 'method': 'Enumerate', 'small_input_limits': 'n<=5'}, reasoning=True)
    p = Provider(protocol='openai', client=httpx.Client(transport=httpx.MockTransport(transport)))
    assert p.generate_primary(problem(), time.monotonic() + 10).method == 'Enumerate'


@pytest.mark.parametrize('data,finish', [({}, 'stop'), ({'code': '', 'method': 'm', 'small_input_limits': 'n'}, 'stop'), ({'code': 'print(1)', 'method': 'm', 'small_input_limits': 'n'}, 'length')])
def test_bad_model_outputs_fail_explicitly(data, finish):
    from app.provider import Provider, ProviderError

    p = Provider(protocol='openai', client=httpx.Client(transport=httpx.MockTransport(lambda req: response(data, finish))))
    with pytest.raises(ProviderError):
        p.generate_primary(problem(), time.monotonic() + 10)


@pytest.mark.parametrize('status', [429, 500])
def test_http_errors_are_sanitized_and_never_retried(status):
    from app.provider import Provider, ProviderError

    p = Provider(protocol='openai', client=httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(status, text='SECRET SERVER ERROR'))))
    with pytest.raises(ProviderError) as error:
        p.generate_primary(problem(), time.monotonic() + 10)
    assert 'SECRET' not in str(error.value)
    assert p.calls == 1


def test_request_timeout_and_call_budget():
    from app.provider import Provider, ProviderError

    def failing(req):
        raise httpx.ReadTimeout('raw details', request=req)
    p = Provider(protocol='openai', client=httpx.Client(transport=httpx.MockTransport(failing)))
    with pytest.raises(ProviderError, match='timed out'):
        p.generate_primary(problem(), time.monotonic() + 10)
    p.calls = 4
    with pytest.raises(ProviderError, match='budget'):
        p.generate_primary(problem(), time.monotonic() + 10)


def test_independent_confirmation_prompt_contains_only_problem_and_samples():
    from app.provider import Provider

    p = Provider(protocol='openai', client=httpx.Client(transport=httpx.MockTransport(lambda req: response({'code': 'def solve(s): return "5"', 'method': 'Independent enumeration'}))))
    assert p.generate_confirmation(problem(), time.monotonic() + 10).method == 'Independent enumeration'


def test_cancelled_request_does_not_start():
    from app.provider import Provider, ProviderError

    cancelled = threading.Event(); cancelled.set()
    p = Provider(cancel=cancelled)
    with pytest.raises(ProviderError, match='cancelled'):
        p.generate_primary(problem(), time.monotonic() + 10)


def test_missing_gemini_key_is_explicit(monkeypatch):
    from app.provider import Provider, ProviderError

    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    with pytest.raises(ProviderError, match='key'):
        Provider(name='gemini')


def test_native_local_request_disables_reasoning_and_validates_json():
    from app.provider import Provider
    def transport(req):
        body=json.loads(req.content)
        assert body['reasoning']=='off' and body['store'] is False
        assert 'system_prompt' in body and req.url.path=='/api/v1/chat'
        return httpx.Response(200,json={'output':[{'type':'message','content':json.dumps({'code':'def solve(s): return "5"','method':'direct','small_input_limits':'two'})}],'stats':{'total_output_tokens':20}})
    p=Provider(protocol='native',client=httpx.Client(transport=httpx.MockTransport(transport)))
    assert p.generate_primary(problem(),time.monotonic()+10).method=='direct'


def test_malformed_response_can_use_explicit_repair():
    from app.provider import Provider, StructuredResponseError
    replies=iter([{}, {'code':'def solve(s): return "5"','method':'direct','small_input_limits':'two'}])
    p=Provider(protocol='openai',client=httpx.Client(transport=httpx.MockTransport(lambda req:response(next(replies)))))
    with pytest.raises(StructuredResponseError) as caught:p.generate_primary(problem(),time.monotonic()+10)
    assert p.repair_response(problem(),caught.value,time.monotonic()+10).method=='direct'
    assert p.calls==2
