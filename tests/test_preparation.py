from pathlib import Path
import time

import pytest


def test_primary_checks_sample_and_generator_roundtrip(tmp_path):
    from app.contracts import GeneratedBundle, ProblemInput, SamplePair
    from app.preparation import prepare_primary
    from app.runner import Runner

    bundle = GeneratedBundle(code=Path('tests/fixtures/sum_bundle.py').read_text(), method='Enumerate two integers', small_input_limits='Two integers')
    problem = ProblemInput(statement='Sum two integers.', samples=[SamplePair(stdin='2 3', stdout='5')])
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
