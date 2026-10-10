from pathlib import Path
import threading
import time

from app.contracts import ConfirmationBundle, GeneratedBundle, ProblemInput, SamplePair

CORRECT = '#include <bits/stdc++.h>\nint main(){long long a,b;std::cin>>a>>b;std::cout<<a+b;}'
WRONG = '#include <bits/stdc++.h>\nint main(){long long a,b;std::cin>>a>>b;std::cout<<std::abs(a+b);}'


class FixtureProvider:
    name = 'fixture'
    calls = 0

    def __init__(self, wrong_primary=False, wrong_confirmation=False):
        self.code = Path('tests/fixtures/sum_bundle.py').read_text()
        if wrong_primary:
            self.code = self.code.replace('return str(sum(parse(stdin)))', 'return str(abs(sum(parse(stdin))))')
        self.wrong_confirmation = wrong_confirmation

    def generate_primary(self, problem, deadline):
        self.calls += 1
        return GeneratedBundle(code=self.code, method='Enumerate two integers', small_input_limits='Two values')

    def generate_confirmation(self, problem, deadline):
        self.calls += 1
        return ConfirmationBundle(code='def valid_input(s):\n try:\n  a=list(map(int,s.split()));return len(a)==2 and all(-100<=x<=100 for x in a)\n except ValueError:return False\ndef solve(s):return str(' + ('999' if self.wrong_confirmation else 'sum(map(int,s.split()))') + ')', method='Independent direct definition')

    def explain(self, evidence, source, method, deadline):
        self.calls += 1
        return 'Fixture explanation: the observed outputs differ.'


def run(tmp_path, source, provider=None, seconds=20):
    from app.search import search

    problem = ProblemInput(statement='Two integers in [-100,100], output their sum.', samples=[SamplePair(stdin='2 3', stdout='5')])
    return search(problem, source, seed=850, deadline=time.monotonic() + seconds, cancel=threading.Event(), on_progress=lambda *args: None, provider=provider or FixtureProvider(), root=tmp_path, max_cases=8)


def test_wrong_algorithm_yields_executed_corrobated_case(tmp_path):
    result = run(tmp_path, WRONG)
    assert result.outcome == 'corroborated_counterexample', result.message
    assert result.evidence.validators_agree
    assert result.evidence.samples_checked
    assert int(result.evidence.expected) == sum(map(int, result.evidence.stdin.split()))
    assert int(result.evidence.actual.stdout) != int(result.evidence.expected)
    assert result.evidence.confirmation_code
    assert result.evidence.candidate_hash


def test_correct_control_is_only_inconclusive(tmp_path):
    result = run(tmp_path, CORRECT)
    assert result.outcome == 'inconclusive'
    assert result.counts.tested > 0
    assert 'correct' not in result.message.lower()


def test_wrong_primary_that_passes_samples_is_unconfirmed(tmp_path):
    result = run(tmp_path, CORRECT, FixtureProvider(wrong_primary=True))
    assert result.outcome == 'unconfirmed_disagreement'
    assert result.evidence is not None
    assert not result.evidence.references_agree


def test_failed_confirmation_preserves_disagreement(tmp_path):
    result = run(tmp_path, WRONG, FixtureProvider(wrong_confirmation=True))
    assert result.outcome == 'unconfirmed_disagreement'
    assert result.evidence.stdin


def test_target_crash_is_runtime_finding(tmp_path):
    result = run(tmp_path, 'int main(){return 7;}')
    assert result.outcome == 'runtime_finding'
    assert result.evidence.actual.exit_code == 7


def test_compilation_error_is_preparation_failure(tmp_path):
    assert run(tmp_path, 'int main( {').outcome == 'preparation_failure'


def test_cancelled_run_cannot_enter_model_or_runner(tmp_path):
    from app.search import search

    cancel = threading.Event(); cancel.set()
    result = search(ProblemInput(statement='Sum', samples=[SamplePair(stdin='2 3', stdout='5')]), WRONG, seed=1, deadline=time.monotonic()+20, cancel=cancel, on_progress=lambda *args: None, provider=FixtureProvider(), root=tmp_path)
    assert result.outcome == 'cancelled'


def test_invalid_generated_cases_are_counted_and_never_compared(tmp_path):
    provider = FixtureProvider()
    provider.code = provider.code.replace('return [index // 5 - 2, index % 5 - 2] if index < 25 else None', 'return [999, 999] if index > 0 else [0,0]')
    result = run(tmp_path, CORRECT, provider)
    assert result.outcome == 'inconclusive'
    assert result.counts.invalid > 0


def test_only_one_repair_is_shared_across_references(tmp_path):
    class RepairProvider(FixtureProvider):
        repairs=0
        def generate_primary(self,problem,deadline):
            bundle=super().generate_primary(problem,deadline)
            return bundle.model_copy(update={'code':'broken python !'})
        def repair(self,problem,bundle,error,deadline):
            self.calls+=1;self.repairs+=1
            return GeneratedBundle(code=self.code,method='sum',small_input_limits='two')
    provider=RepairProvider(wrong_confirmation=True)
    result=run(tmp_path,WRONG,provider)
    assert result.outcome=='unconfirmed_disagreement'
    assert provider.repairs==1 and provider.calls==3
    assert result.method=='sum'


def test_interrupted_reduction_preserves_last_corroborated_input(tmp_path):
    from app.search import search
    cancel=threading.Event()
    def progress(stage,*args):
        if stage=='reducing':cancel.set()
    result=search(ProblemInput(statement='Sum of two integers [-100,100]',samples=[SamplePair(stdin='2 3',stdout='5')]),WRONG,provider=FixtureProvider(),root=tmp_path,cancel=cancel,on_progress=progress,deadline=time.monotonic()+30)
    assert result.outcome=='corroborated_counterexample'
    assert result.evidence.references_agree
    assert result.evidence.stdin.strip()=='-2 -2'


def test_malformed_bundle_uses_shared_repair_allowance(tmp_path):
    from app.provider import StructuredResponseError
    class MalformedProvider(FixtureProvider):
        repairs=0
        def generate_primary(self,problem,deadline):
            self.calls+=1
            raise StructuredResponseError(GeneratedBundle,'{}')
        def repair_response(self,problem,error,deadline):
            self.calls+=1;self.repairs+=1
            return GeneratedBundle(code=self.code,method='sum',small_input_limits='two')
    provider=MalformedProvider(wrong_confirmation=True)
    result=run(tmp_path,WRONG,provider)
    assert result.outcome=='unconfirmed_disagreement'
    assert provider.repairs==1 and provider.calls==3


def test_reported_elapsed_includes_container_cleanup(tmp_path):
    from app.search import search
    from app.runner import CompilationError
    from app.contracts import ExecutionResult
    class InertRunner:
        def compile_cpp(self,*args,**kwargs):raise CompilationError(ExecutionResult(status='runtime_error',stderr='syntax error'))
        def close(self,deadline):time.sleep(.04);return True
    result=search(ProblemInput(statement='Sum',samples=[SamplePair(stdin='2 3',stdout='5')]),WRONG,provider=FixtureProvider(),runner=InertRunner(),deadline=time.monotonic()+1)
    assert result.elapsed>=.04 and result.outcome=='preparation_failure'


def test_compilation_cancellation_is_classified_as_cancelled():
    from app.search import search
    from app.runner import CompilationError
    from app.contracts import ExecutionResult
    cancel=threading.Event()
    class InterruptedRunner:
        def compile_cpp(self,*args,**kwargs):
            cancel.set()
            raise CompilationError(ExecutionResult(status='cancelled'))
        def close(self,deadline):return True
    result=search(ProblemInput(statement='Sum',samples=[SamplePair(stdin='2 3',stdout='5')]),WRONG,provider=FixtureProvider(),runner=InterruptedRunner(),cancel=cancel,deadline=time.monotonic()+10)
    assert result.outcome=='cancelled'


def test_repeating_exhaustive_generator_yields_to_other_modes(tmp_path):
    from app.search import search
    provider=FixtureProvider()
    provider.code=provider.code.replace('return [index // 5 - 2, index % 5 - 2] if index < 25 else None','return [0,0]')
    result=search(ProblemInput(statement='Sum integers [-100,100]',samples=[SamplePair(stdin='2 3',stdout='5')]),WRONG,provider=provider,root=tmp_path,deadline=time.monotonic()+30,max_cases=16)
    assert result.outcome=='corroborated_counterexample'
