from pathlib import Path

from tests.test_search import WRONG, FixtureProvider, run


def test_reduction_keeps_valid_confirmed_failure(tmp_path):
    result = run(tmp_path, WRONG)
    values = list(map(int, result.evidence.stdin.split()))
    assert len(values) == 2
    assert sum(abs(x) for x in values) == 1
    assert result.evidence.validators_agree
    assert result.evidence.expected == '-1'
    assert result.evidence.actual.stdout == '1'


def test_invalid_duplicate_and_nonimproving_shrinks_are_rejected(tmp_path):
    provider = FixtureProvider()
    provider.code = provider.code.replace('return [[0, case[1]], [case[0], 0], [int(case[0] / 2), int(case[1] / 2)]]', 'return [[999,999],case,case,[case[0]],[-100,-100]]')
    result = run(tmp_path, WRONG, provider)
    assert result.outcome == 'corroborated_counterexample'
    assert list(map(int,result.evidence.stdin.split())) == [-2,-2]


def test_complexity_counts_tokens_then_absolute_values():
    from app.search import complexity

    assert complexity('2 -3 4') == (3,9)
    assert complexity('1 99') < complexity('2 0 0')
