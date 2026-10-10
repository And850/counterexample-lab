from pathlib import Path
import time

import pytest


def test_primary_checks_sample_and_generator_roundtrip(tmp_path):
    import json
    import httpx
    from app.contracts import ProblemInput, SamplePair
    from app.provider import Provider
    from app.preparation import prepare_primary
    from app.runner import Runner

    problem = ProblemInput(statement='Sum two integers.', samples=[SamplePair(stdin='2 3', stdout='5')])
    wire = {'code_lines': Path('tests/fixtures/sum_bundle.py').read_text().splitlines(), 'method':'Enumerate two integers', 'small_input_limits':'Two integers'}
    provider = Provider(protocol='openai', client=httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(wire)}}]}))))
    bundle = provider.generate_primary(problem, time.monotonic()+15)
    runner = Runner(tmp_path)
    try:
        harness = prepare_primary(runner, bundle, problem, time.monotonic() + 15)
        assert harness.call('generate', seed=1, index=0, mode='exhaustive')['case'] == [-2, -2]
    finally:
        runner.close()


@pytest.mark.parametrize('code', ['this is not valid Python !', Path('tests/fixtures/sum_bundle.py').read_text().replace('return str(sum(parse(stdin)))', 'return "999"')], ids=['syntax', 'sample-mismatch'])
def test_unchecked_reference_cannot_enter_search(tmp_path, code):
    from app.contracts import GeneratedBundle, ProblemInput, SamplePair
    from app.preparation import prepare_primary, PreparationError
    from app.runner import Runner

    runner = Runner(tmp_path)
    bundle = GeneratedBundle(code=code, method='Enumerate', small_input_limits='Two integers')
    problem = ProblemInput(statement='Sum.', samples=[SamplePair(stdin='2 3', stdout='5')])
    try:
        with pytest.raises(PreparationError):
            prepare_primary(runner, bundle, problem, time.monotonic() + 10)
    finally:
        runner.close()
