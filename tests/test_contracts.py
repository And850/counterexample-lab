import pytest
from pydantic import ValidationError


def test_problem_requires_explicit_complete_samples_before_run():
    from app.contracts import ProblemInput, RunRequest

    problem = ProblemInput(statement='Find maximum.', samples=[])
    with pytest.raises(ValidationError):
        RunRequest(problem=problem, source='int main(){}')
    with pytest.raises(ValidationError):
        ProblemInput(statement='   ')


def test_source_and_statement_bounds_are_enforced():
    from app.contracts import ProblemInput, RunRequest, SamplePair

    with pytest.raises(ValidationError):
        ProblemInput(statement='x' * 100001)
    problem = ProblemInput(statement='Sum two integers.', samples=[SamplePair(stdin='2 3', stdout='5')])
    with pytest.raises(ValidationError):
        RunRequest(problem=problem, source='x' * 262145)


def test_generated_code_must_be_nonempty_and_bounded():
    from app.contracts import GeneratedBundle

    with pytest.raises(ValidationError):
        GeneratedBundle(code='', method='Brute force', small_input_limits='n<=5')
    with pytest.raises(ValidationError):
        GeneratedBundle(code='x' * 262145, method='Brute force', small_input_limits='n<=5')


def test_worker_messages_bound_case_lists_and_json_shape():
    from app.contracts import WorkerReply

    assert WorkerReply(value={'a': [1, 2]}, cases=[]).model_dump()['value'] == {'a': [1, 2]}
    with pytest.raises(ValidationError):
        WorkerReply(cases=[{}] * 65)
    with pytest.raises(ValidationError):
        WorkerReply(value={'invalid': float('nan')})


def test_results_cannot_claim_confirmation_without_evidence():
    from app.contracts import CounterexampleResult

    with pytest.raises(ValidationError):
        CounterexampleResult(outcome='corroborated_counterexample', message='Found')
    assert CounterexampleResult(outcome='inconclusive', message='No case within limits').outcome == 'inconclusive'
