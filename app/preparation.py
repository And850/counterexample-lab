import json
from pathlib import Path
import time

from app.outputs import integer_tokens
from app.runner import Handle, Runner

DRIVER = Path(__file__).resolve().parent.parent / 'runner' / 'harness.py'


class PreparationError(RuntimeError):
    pass


class Harness:
    def __init__(self, runner: Runner, handle: Handle, deadline: float, confirmation=False):
        self.runner = runner
        self.handle = handle
        self.deadline = deadline
        self.confirmation = confirmation

    def call(self, op, **parameters):
        request = json.dumps({'op': op, 'confirmation': self.confirmation, **parameters}, allow_nan=False)
        result = self.runner.execute(self.handle, request, self.deadline)
        if result.status != 'ok':
            raise PreparationError('Reference operation ' + op + ' failed: ' + result.status + '\n' + result.stderr[-1200:])
        try:
            value = json.loads(result.stdout)
            if not isinstance(value, dict):
                raise ValueError('Expected object')
            # Reject nonfinite and oversized structured values at the host boundary.
            from app.contracts import WorkerReply
            WorkerReply(value=value, cases=value.get('cases', []))
            return value
        except (ValueError, TypeError) as error:
            raise PreparationError('Reference returned invalid JSON') from error


def prepare_primary(runner, bundle, problem, deadline):
    handle = runner.prepare('primary', {'main.py': DRIVER.read_text(), 'generated.py': bundle.code}, deadline=deadline)
    harness = Harness(runner, handle, deadline)
    harness.call('check')
    for sample in problem.samples:
        reply = harness.call('sample', stdin=sample.stdin)
        try:
            checked = reply['valid'] is True and reply['roundtrip'] is True and integer_tokens(reply['rendered']) == integer_tokens(sample.stdin) and integer_tokens(reply['output']) == integer_tokens(sample.stdout)
        except (ValueError, KeyError, TypeError):
            checked = False
        if not checked:
            raise PreparationError('Primary reference failed sample. stdin and rendered output must be raw whitespace text, never JSON. Required stdin: ' + repr(sample.stdin[:200]) + '; rendered: ' + repr(reply.get('rendered'))[:200] + '; reference output: ' + repr(reply.get('output'))[:200] + '; required answer: ' + repr(sample.stdout[:200]))
    for mode in ('exhaustive', 'random', 'adversarial'):
        reply = harness.call('generate', seed=850, index=0, mode=mode)
        if reply.get('case') is not None and (reply.get('valid') is not True or reply.get('roundtrip') is not True):
            raise PreparationError('Generator failed validity or round trip')
    return harness


def prepare_confirmation(runner, bundle, problem, deadline):
    handle = runner.prepare('confirmation', {'main.py': DRIVER.read_text(), 'generated.py': bundle.code}, deadline=deadline)
    harness = Harness(runner, handle, deadline, confirmation=True)
    harness.call('check')
    for sample in problem.samples:
        reply = harness.call('confirm', stdin=sample.stdin)
        try:
            checked = reply['valid'] is True and integer_tokens(reply['output']) == integer_tokens(sample.stdout)
        except (ValueError, KeyError, TypeError):
            checked = False
        if not checked:
            raise PreparationError('Confirmation reference failed samples or validity')
    return harness
