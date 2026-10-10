import json
import threading
import time

import httpx
import pytest


def problem():
    from app.contracts import ProblemInput, SamplePair

    return ProblemInput(statement='Sum two integers in [-100,100].', samples=[SamplePair(stdin='2 3', stdout='5')])


def wire(data):
    data=dict(data)
    if "code" in data:
        code=data.pop("code")
        data["code_lines"]=code.splitlines()
    return data


def response(data, finish='stop', reasoning=False):
    return httpx.Response(200, json={'choices': [{'finish_reason': finish, 'message': {'content': '' if reasoning else json.dumps(wire(data)), 'reasoning_content': json.dumps(wire(data)) if reasoning else ''}}]})


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
        return httpx.Response(200,json={'output':[{'type':'message','content':json.dumps(wire({'code':'def solve(s): return "5"','method':'direct','small_input_limits':'two'}))}],'stats':{'total_output_tokens':20}})
    p=Provider(protocol='native',client=httpx.Client(transport=httpx.MockTransport(transport)))
    assert p.generate_primary(problem(),time.monotonic()+10).method=='direct'


def test_malformed_response_can_use_explicit_repair():
    from app.provider import Provider, StructuredResponseError
    replies=iter([{}, {'code':'def solve(s): return "5"','method':'direct','small_input_limits':'two'}])
    p=Provider(protocol='openai',client=httpx.Client(transport=httpx.MockTransport(lambda req:response(next(replies)))))
    with pytest.raises(StructuredResponseError) as caught:p.generate_primary(problem(),time.monotonic()+10)
    assert p.repair_response(problem(),caught.value,time.monotonic()+10).method=='direct'
    assert p.calls==2


def test_openai_api_separates_module_instructions_from_problem_data():
    from app.provider import Provider
    def transport(req):
        body=json.loads(req.content)
        assert [message['role'] for message in body['messages']]==['system','user']
        assert 'ALL SIX' in body['messages'][0]['content']
        assert 'Sum two integers' in body['messages'][1]['content']
        return response({'code':'def solve(s): return "5"','method':'definition','small_input_limits':'two'})
    p=Provider(protocol='openai',client=httpx.Client(transport=httpx.MockTransport(transport)))
    assert p.generate_primary(problem(),time.monotonic()+10).method=='definition'


def test_native_nonreasoning_model_omits_unsupported_setting(monkeypatch):
    from app.provider import Provider
    monkeypatch.setenv('LMSTUDIO_REASONING','unsupported')
    def transport(req):
        body=json.loads(req.content)
        assert 'reasoning' not in body
        return httpx.Response(200,json={'output':[{'type':'message','content':json.dumps(wire({'code':'def solve(s): return "5"','method':'direct','small_input_limits':'two'}))}],'stats':{'total_output_tokens':20}})
    p=Provider(protocol='native',client=httpx.Client(transport=httpx.MockTransport(transport)))
    assert p.generate_primary(problem(),time.monotonic()+10).method=='direct'


def test_complete_json_fence_is_accepted_but_surrounding_prose_is_not():
    from app.provider import Provider, StructuredResponseError
    bundle={'code':'def solve(s): return "5"','method':'direct','small_input_limits':'two'}
    def model(raw):
        return Provider(protocol='openai',client=httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':raw}}]}))))
    raw='```json\n'+json.dumps(wire(bundle))+'\n```'
    assert model(raw).generate_primary(problem(),time.monotonic()+10).method=='direct'
    with pytest.raises(StructuredResponseError):
        model('Here is the result:\n'+raw).generate_primary(problem(),time.monotonic()+10)


def test_wire_code_lines_preserve_python_indentation_and_blank_lines():
    from app.provider import Provider
    lines=['def solve(s):','    a, b = map(int, s.split())','    return str(a + b)','']
    p=Provider(protocol='openai',client=httpx.Client(transport=httpx.MockTransport(lambda req:response({'code_lines':lines,'method':'direct','small_input_limits':'two'}))))
    assert p.generate_primary(problem(),time.monotonic()+10).code=='\n'.join(lines)


@pytest.mark.parametrize('lines',[['def solve(s):\n    return "5"'],['x'*4097],['x']*257])
def test_wire_source_limits_reject_embedded_breaks_or_oversized_lines(lines):
    from app.provider import Provider,StructuredResponseError
    p=Provider(protocol='openai',client=httpx.Client(transport=httpx.MockTransport(lambda req:response({'code_lines':lines,'method':'direct','small_input_limits':'two'}))))
    with pytest.raises(StructuredResponseError):p.generate_primary(problem(),time.monotonic()+10)


def test_gemini_quota_error_is_explicit_sanitized_and_not_retried(monkeypatch):
    from google import genai
    from google.genai import errors
    from app.provider import Provider,ProviderError
    monkeypatch.setenv('GEMINI_API_KEY','test-only-placeholder')
    class Models:
        calls=0
        async def generate_content(self,**kwargs):
            self.calls+=1
            raise errors.ClientError(429,{'error':{'message':'SECRET details','status':'RESOURCE_EXHAUSTED'}})
    class Aio:
        models=Models()
        closed=False
        async def aclose(self):self.closed=True
    class Client:aio=Aio()
    client=Client()
    monkeypatch.setattr(genai,'Client',lambda **kwargs:client)
    p=Provider(name='gemini')
    with pytest.raises(ProviderError,match='quota') as caught:p.generate_primary(problem(),time.monotonic()+10)
    assert 'SECRET' not in str(caught.value)
    assert p.calls==1 and client.aio.models.calls==1 and client.aio.closed
