"""Bounded differential search. Only executed reference consensus is corroborated."""
import hashlib
from pathlib import Path
import threading
import time

from app.contracts import Counts, CounterexampleResult, Evidence
from app.outputs import integer_tokens
from app.preparation import PreparationError, prepare_confirmation, prepare_primary
from app.provider import Provider, ProviderError, StructuredResponseError
from app.runner import CompilationError, Runner, RunnerError


def complexity(stdin):
    values = integer_tokens(stdin)
    return len(values), sum(abs(value) for value in values)


def same(left, right):
    try:
        return integer_tokens(left) == integer_tokens(right)
    except (ValueError, TypeError):
        return False


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def search(problem, source, *, seed=850, deadline=None, cancel=None, on_progress=None,
           provider=None, root=Path('.runs'), max_cases=10000, runner=None):
    started = time.monotonic()
    hard_deadline = min(deadline or started + 180, started + 180)
    # Reserve bounded time for concurrent Docker cleanup.
    deadline = max(started, hard_deadline - min(5, (hard_deadline-started)/10))
    returned = None
    first_deadline = min(deadline, started + 120)
    cancel = cancel or threading.Event()
    counts = Counts()
    evidence = None
    method = ''
    explanation = ''
    repaired = False
    stage = 'preparing'

    def progress(value):
        nonlocal stage
        stage = value
        if on_progress:
            on_progress(stage, counts.model_copy(), time.monotonic() - started)

    def result(outcome, message):
        nonlocal returned
        returned = CounterexampleResult(outcome=outcome, message=message, evidence=evidence,
            seed=seed, counts=counts, elapsed=time.monotonic()-started, method=method,
            explanation=explanation, explanation_ai_generated=bool(explanation and provider.name != 'fixture'))
        return returned

    def stopped(limit=deadline):
        return cancel.is_set() or time.monotonic() >= limit

    if cancel.is_set():
        return result('cancelled', 'Cancelled before preparation.')
    if stopped():
        return result('inconclusive', 'Time budget expired before preparation.')
    runner = runner or Runner(root, deadline=deadline)
    runner.deadline = deadline
    try:
        provider = provider or Provider(cancel=cancel)
        progress('compiling')
        candidate = runner.compile_cpp(source, deadline=deadline)
        progress('generating primary reference')
        def generate(function):
            nonlocal repaired
            try:
                return function(problem, deadline)
            except StructuredResponseError as error:
                if repaired or stopped():
                    raise
                repaired = True
                progress('repairing structured response')
                return provider.repair_response(problem, error, deadline)

        bundle = generate(provider.generate_primary)
        method = bundle.method

        def prepare(function, value):
            nonlocal repaired
            try:
                return function(runner, value, problem, deadline), value
            except PreparationError as error:
                if repaired or stopped() or not hasattr(provider, 'repair'):
                    raise
                repaired = True
                replacement = provider.repair(problem, value, error, deadline)
                return function(runner, replacement, problem, deadline), replacement

        progress('checking primary samples')
        primary, bundle = prepare(prepare_primary, bundle)
        method = bundle.method
        progress('searching')
        primary.deadline = first_deadline
        seen = set()
        failing_case = None
        last_duplicate = False

        def examine(stdin, case):
            nonlocal evidence, failing_case, last_duplicate
            last_duplicate = False
            if not isinstance(stdin, str) or len(stdin.encode()) > 100000:
                counts.invalid += 1
                return None
            try:
                key = integer_tokens(stdin)
            except ValueError:
                counts.invalid += 1
                return None
            if key in seen:
                last_duplicate = True
                return None
            seen.add(key)
            if primary.call('validate', stdin=stdin).get('valid') is not True:
                counts.invalid += 1
                return None
            counts.valid += 1
            expected = primary.call('solve', stdin=stdin).get('output')
            try:
                integer_tokens(expected)
            except (ValueError, TypeError) as error:
                raise PreparationError('Primary reference produced a noninteger answer') from error
            actual = runner.execute(candidate, stdin, first_deadline)
            counts.tested += 1
            if actual.status == 'cancelled':
                return 'cancelled'
            if actual.status == 'runner_error':
                raise RunnerError('Candidate execution transport failed')
            if actual.status == 'timeout':
                counts.timed_out += 1
                if stopped(first_deadline):
                    return None
            if actual.status != 'ok' or not same(expected, actual.stdout):
                evidence = Evidence(stdin=stdin, expected=expected, actual=actual,
                    samples_checked=True, primary_code=bundle.code,
                    candidate_hash=digest(source), primary_hash=digest(bundle.code))
                failing_case = case
                return 'disagreement' if actual.status == 'ok' else 'runtime'
            return None

        found = None
        for sample in problem.samples:
            if stopped(first_deadline):
                break
            reply = primary.call('sample', stdin=sample.stdin)
            found = examine(sample.stdin, reply['case'])
            if found:
                break
        exhaustive = True
        repeated_exhaustive = 0
        exhaustive_until = min(first_deadline, time.monotonic() + min(20, max(0, first_deadline-time.monotonic())*.3))
        exhaustive_index = random_index = adversarial_index = 0
        while not found and not stopped(first_deadline) and counts.generated < min(max_cases, 10000):
            if exhaustive and exhaustive_index < 256 and repeated_exhaustive < 8 and time.monotonic() < exhaustive_until:
                mode, index = 'exhaustive', exhaustive_index
                exhaustive_index += 1
            else:
                exhaustive = False
                if (random_index + adversarial_index) % 2 == 0:
                    mode, index = 'random', random_index
                    random_index += 1
                else:
                    mode, index = 'adversarial', adversarial_index
                    adversarial_index += 1
            reply = primary.call('generate', seed=seed, index=index, mode=mode)
            counts.generated += 1
            progress('searching')
            if reply.get('case') is None:
                if mode == 'exhaustive':
                    exhaustive = False
                continue
            if reply.get('valid') is not True or reply.get('roundtrip') is not True:
                counts.invalid += 1
                continue
            found = examine(reply.get('rendered'), reply['case'])
            if mode == 'exhaustive':
                repeated_exhaustive = repeated_exhaustive + 1 if last_duplicate else 0
        if found == 'cancelled' or cancel.is_set():
            return result('cancelled', 'Cancelled; any observed evidence is retained.')
        if found == 'runtime':
            return result('runtime_finding', 'Candidate failed during execution on a primary-validated input; this is not output corroboration.')
        if not evidence:
            return result('inconclusive', 'No disagreement found within the tested cases and limits.')
        if stopped():
            return result('unconfirmed_disagreement', 'Observed disagreement; independent checks could not finish within the budget.')
        primary.deadline = deadline
        progress('generating independent reference')
        try:
            confirmation_bundle = generate(provider.generate_confirmation)
            confirmation, confirmation_bundle = prepare(prepare_confirmation, confirmation_bundle)
            evidence.confirmation_code = confirmation_bundle.code
            evidence.confirmation_hash = digest(confirmation_bundle.code)
            reply = confirmation.call('confirm', stdin=evidence.stdin)
            evidence.confirmation = reply.get('output')
            evidence.validators_agree = primary.call('validate', stdin=evidence.stdin).get('valid') is True and reply.get('valid') is True
            evidence.references_agree = same(evidence.expected, evidence.confirmation)
            if not evidence.validators_agree or not evidence.references_agree:
                return result('unconfirmed_disagreement', 'Independent references or input validators did not agree.')
        except (PreparationError, ProviderError, RunnerError):
            return result('unconfirmed_disagreement', 'Observed disagreement; independent reference preparation or execution failed.')
        progress('reducing')
        proposals_seen = {integer_tokens(evidence.stdin)}
        while not stopped():
            improved = False
            try:
                proposals = primary.call('shrink', case=failing_case).get('cases', [])
                for proposal in proposals:
                    if stopped():
                        break
                    rendered = primary.call('render', case=proposal)
                    stdin = rendered.get('rendered')
                    try:
                        key = integer_tokens(stdin)
                        smaller = complexity(stdin) < complexity(evidence.stdin)
                    except (ValueError, TypeError):
                        continue
                    if key in proposals_seen:
                        continue
                    proposals_seen.add(key)
                    if not smaller or rendered.get('valid') is not True or primary.call('validate', stdin=stdin).get('valid') is not True:
                        continue
                    secondary = confirmation.call('confirm', stdin=stdin)
                    expected = primary.call('solve', stdin=stdin).get('output')
                    if secondary.get('valid') is not True or not same(expected, secondary.get('output')):
                        continue
                    actual = runner.execute(candidate, stdin, deadline)
                    if actual.status == 'ok' and not same(expected, actual.stdout):
                        evidence = evidence.model_copy(update={'stdin': stdin, 'expected': expected, 'confirmation': secondary['output'], 'actual': actual})
                        failing_case = proposal
                        improved = True
                        break
                if not improved:
                    break
            except (PreparationError, RunnerError):
                break
        if not stopped() and provider.calls < 4:
            progress('explaining')
            try:
                explanation = provider.explain(evidence, source, method, deadline)
            except ProviderError:
                pass
        return result('corroborated_counterexample', 'Both sample-checked references and validators agree on this executed failing input. Reduced locally; global minimality is not claimed.')
    except CompilationError as error:
        if cancel.is_set() or error.result.status == 'cancelled':
            return result('cancelled', 'Cancelled during C++ compilation.')
        return result('preparation_failure', 'C++ compilation failed.\n' + error.result.stderr[-2000:])
    except PreparationError as error:
        if stage == 'searching' and time.monotonic() >= first_deadline and not cancel.is_set():
            counts.timed_out += 1
            return result('inconclusive', 'No disagreement found within the tested cases and limits.')
        return result('cancelled' if cancel.is_set() else 'preparation_failure', str(error))
    except ProviderError as error:
        return result('cancelled' if cancel.is_set() else 'provider_failure', str(error))
    except RunnerError as error:
        return result('cancelled' if cancel.is_set() else 'runner_failure', str(error))
    finally:
        cleaned = runner.close(deadline=hard_deadline)
        if returned:
            returned.elapsed = time.monotonic()-started
            if not cleaned:
                returned.message += ' Container cleanup could not be verified; inspect Docker before another run.'
