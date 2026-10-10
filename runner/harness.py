"""Trusted JSON driver; generated modules are imported only in a role container."""
import contextlib
import importlib.util
import io
import json
import sys

sys.set_int_max_str_digits(0)


class Captured(io.TextIOBase):
    def __init__(self):
        self.size = 0

    def write(self, text):
        self.size += len(text.encode())
        if self.size > 65536:
            raise ValueError('Generated diagnostics exceed limit')
        return len(text)


def main():
    request = json.loads(sys.stdin.read(1000000))
    captured = Captured()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        spec = importlib.util.spec_from_file_location('generated', '/sources/generated.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        op = request['op']
        result = {}
        if op == 'check':
            required = ['valid_input', 'solve'] if request.get('confirmation') else ['parse', 'render', 'valid', 'solve', 'generate', 'shrink']
            if not all(callable(getattr(module, name, None)) for name in required):
                raise ValueError('Missing required module functions: ' + ', '.join(name for name in required if not callable(getattr(module, name, None))))
            result = {'value': True}
        elif op == 'sample':
            case = module.parse(request['stdin'])
            rendered = module.render(case)
            result = {'case': case, 'rendered': rendered, 'valid': module.valid(case), 'roundtrip': module.parse(rendered) == case, 'output': module.solve(request['stdin'])}
        elif op == 'generate':
            case = module.generate(request['seed'], request['index'], request['mode'])
            result = {'case': case}
            if case is not None:
                rendered = module.render(case)
                result.update({'rendered': rendered, 'valid': module.valid(case), 'roundtrip': module.parse(rendered) == case})
        elif op == 'solve':
            result = {'output': module.solve(request['stdin'])}
        elif op == 'validate':
            valid = module.valid_input(request['stdin']) if request.get('confirmation') else module.valid(module.parse(request['stdin']))
            result = {'valid': valid}
        elif op == 'confirm':
            result = {'valid': module.valid_input(request['stdin']), 'output': module.solve(request['stdin'])}
        elif op == 'shrink':
            cases = module.shrink(request['case'])
            if not isinstance(cases, list) or len(cases) > 64:
                raise ValueError('Reducer exceeds proposal bound')
            result = {'cases': cases}
        elif op == 'render':
            result = {'rendered': module.render(request['case']), 'valid': module.valid(request['case'])}
        else:
            raise ValueError('Unknown module operation')
    encoded = json.dumps(result, allow_nan=False)
    if len(encoded.encode()) > 48000:
        raise ValueError('Harness reply exceeds limit')
    print(encoded)


if __name__ == '__main__':
    main()
