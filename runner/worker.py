"""Trusted one-request worker. Untrusted programs never share protocol pipes."""
import ctypes
import json
import os
from pathlib import Path
import resource
import selectors
import signal
import subprocess
import sys
import time

OUTPUT_LIMIT = 65536
MESSAGE_LIMIT = 1024 * 1024


def restrict_child():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024 * 1024,) * 2)


def cleanup(process):
    # Process groups catch ordinary forks; /proc also catches setsid/double-fork.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=.25)
    until = time.monotonic() + .5
    while True:
        remaining = [int(entry.name) for entry in Path('/proc').iterdir()
                     if entry.name.isdigit() and int(entry.name) not in (1, os.getpid())]
        if not remaining:
            return
        if time.monotonic() >= until:
            raise RuntimeError('Descendants did not quiesce')
        for pid in remaining:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        time.sleep(.005)


def execute(request):
    started = time.monotonic()
    timeout = min(float(request['timeout']), 20 if request.get('compile') else 2)
    argv = request['argv']
    if not isinstance(argv, list) or not all(isinstance(arg, str) for arg in argv):
        raise ValueError('Invalid argument vector')
    data = request['stdin'].encode('utf-8')
    if len(data) > MESSAGE_LIMIT:
        raise ValueError('Input exceeds limit')
    output = {'stdout': bytearray(), 'stderr': bytearray()}
    status = None
    process = subprocess.Popen(
        argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True, preexec_fn=restrict_child, cwd='/work',
        env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp', 'LANG': 'C.UTF-8'},
    )
    try:
        with selectors.DefaultSelector() as selector:
            for name in ('stdout', 'stderr'):
                pipe = getattr(process, name)
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, name)
            if data:
                os.set_blocking(process.stdin.fileno(), False)
                selector.register(process.stdin, selectors.EVENT_WRITE, 'stdin')
            else:
                process.stdin.close()
            offset = 0
            while selector.get_map():
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    status = 'timeout'
                    break
                for key, _ in selector.select(min(remaining, .05)):
                    if key.data == 'stdin':
                        try:
                            offset += os.write(key.fd, data[offset:offset + 8192])
                        except BrokenPipeError:
                            offset = len(data)
                        if offset == len(data):
                            selector.unregister(key.fileobj)
                            key.fileobj.close()
                    else:
                        chunk = os.read(key.fd, 8192)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        buffer = output[key.data]
                        capacity = OUTPUT_LIMIT - len(buffer)
                        buffer.extend(chunk[:capacity])
                        if len(chunk) > capacity:
                            status = 'output_limit'
                            break
                if status:
                    break
            if status is None:
                # A process can close its output pipes and continue running.
                try:
                    process.wait(timeout=max(.001, timeout - (time.monotonic() - started)))
                    status = 'ok' if process.returncode == 0 else 'runtime_error'
                except subprocess.TimeoutExpired:
                    status = 'timeout'
    finally:
        cleanup(process)
        for pipe in (process.stdin, process.stdout, process.stderr):
            pipe.close()
    return {
        'status': status,
        'stdout': bytes(output['stdout']).decode('utf-8', errors='replace'),
        'stderr': bytes(output['stderr']).decode('utf-8', errors='replace'),
        'exit_code': process.returncode,
        'elapsed': time.monotonic() - started,
    }


if __name__ == '__main__':
    try:
        # PR_SET_DUMPABLE=0 denies same-UID access to the protocol's /proc/fd.
        # No capability is required; fail closed if the kernel rejects it.
        if ctypes.CDLL(None).prctl(4, 0, 0, 0, 0) != 0:
            raise RuntimeError('Cannot protect worker descriptors')
        line = sys.stdin.buffer.readline(MESSAGE_LIMIT + 1)
        if len(line) > MESSAGE_LIMIT:
            raise ValueError('Request exceeds limit')
        result = execute(json.loads(line))
    except Exception:
        result = {'status': 'runner_error', 'stdout': '', 'stderr': 'Container worker failed', 'exit_code': None, 'elapsed': 0}
    sys.stdout.write(json.dumps(result, ensure_ascii=True) + '\n')
