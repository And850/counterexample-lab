"""Docker-only execution; no host fallback for submitted or generated code."""
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import threading
import time
import uuid

from app.contracts import ExecutionResult

IMAGE = 'counterexample-runner:step1'
MESSAGE_LIMIT = 1024 * 1024


class RunnerError(RuntimeError):
    pass


class CompilationError(RunnerError):
    def __init__(self, result: ExecutionResult):
        super().__init__('C++ compilation failed')
        self.result = result


@dataclass
class Handle:
    container: str
    run_id: str
    argv: tuple[str, ...]
    role: str
    sources: Path


def docker(*arguments: str, timeout: float = 10) -> str:
    try:
        result = subprocess.run(['docker', *arguments], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RunnerError('Docker is unavailable or timed out') from error
    if result.returncode:
        raise RunnerError(result.stderr[:4096].strip() or 'Docker command failed')
    return result.stdout.strip()


def readiness() -> dict:
    try:
        version = docker('info', '--format', '{{.ServerVersion}}')
        architecture = docker('image', 'inspect', IMAGE, '--format', '{{.Architecture}}')
        return {'ready': True, 'version': version, 'image': IMAGE, 'architecture': architecture}
    except RunnerError:
        return {'ready': False, 'image': IMAGE, 'error': 'Start Docker and build the runner image.'}


class Runner:
    def __init__(self, root: Path, deadline: float | None = None):
        self.deadline = deadline if deadline is not None else float("inf")
        self.run_id = uuid.uuid4().hex
        self.root = Path(root).resolve() / self.run_id
        self.root.mkdir(parents=True, mode=0o700)
        self._containers: set[str] = set()
        self._poisoned: set[str] = set()
        self._lock = threading.Lock()
        self._operation = threading.Lock()
        self._closed = threading.Event()

    def _sources(self, sources: dict[str, str]) -> Path:
        if not sources or len(sources) > 8:
            raise ValueError('Supply between one and eight source files')
        total = 0
        for name, value in sources.items():
            if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,100}', name):
                raise ValueError('Source filenames must be plain filenames')
            if not isinstance(value, str) or len(value.encode('utf-8')) > 262144:
                raise ValueError('Source file exceeds 256 KiB')
            total += len(value.encode('utf-8'))
        if total > 1048576:
            raise ValueError('Source bundle exceeds 1 MiB')
        directory = self.root / uuid.uuid4().hex
        directory.mkdir(mode=0o755)
        for name, value in sources.items():
            target = directory / name
            target.write_text(value, encoding='utf-8')
            target.chmod(0o444)
        return directory

    def _start(self, role: str, directory: Path, *, compile: bool = False, deadline: float | None = None) -> str:
        if role not in ('submitted', 'primary', 'confirmation'):
            raise ValueError('Unknown runner role')
        if self._closed.is_set():
            raise RunnerError('Runner is closed')
        remaining = min(self.deadline, deadline if deadline is not None else float("inf")) - time.monotonic()
        if remaining <= 0:
            raise RunnerError('Runner lifecycle budget expired')
        name = f'ce-{self.run_id}-{uuid.uuid4().hex[:8]}'
        with self._lock:
            self._containers.add(name)
        try:
            docker(
                'run', '-d', '--name', name, '--label', f'counterexample.run={self.run_id}',
                '--label', f'counterexample.role={role}', '--network', 'none', '--read-only',
                '--log-driver', 'none',
                '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--user', '65534:65534',
                '--memory', '1g' if compile else '512m', '--memory-swap', '1g' if compile else '512m',
                '--cpus', '1', '--pids-limit', '128',
                '--tmpfs', '/work:rw,nosuid,nodev,size=128m,mode=1777' if compile else '/work:rw,nosuid,nodev,size=64m,mode=1777',
                '--tmpfs', '/tmp:rw,nosuid,nodev,size=64m,mode=1777',
                '--mount', f'type=bind,source={directory},target=/sources,readonly', IMAGE, timeout=min(10, remaining),
            )
            if self._closed.is_set():
                raise RunnerError('Runner was cancelled')
            return name
        except BaseException:
            self._remove(name, self.deadline)
            raise

    def prepare(self, role: str, sources: dict[str, str], deadline: float | None = None) -> Handle:
        with self._operation:
            directory = self._sources(sources)
            if 'main.py' not in sources:
                raise ValueError('Python role requires main.py')
            name = self._start(role, directory, deadline=deadline)
            return Handle(name, self.run_id, ('python', '-I', '/sources/main.py'), role, directory)

    def _remove(self, name: str, deadline: float | None = None):
        with self._lock:
            self._poisoned.add(name)
        try:
            docker('rm', '-f', name, timeout=max(.001, min(10, (deadline if deadline is not None else time.monotonic()+10)-time.monotonic())))
        except RunnerError:
            # Do not mask the original failure; close retries every tracked name.
            return
        with self._lock:
            self._containers.discard(name)
            self._poisoned.discard(name)

    def _request(self, container: str, argv: tuple[str, ...], stdin: str, deadline: float, *, compile: bool = False) -> ExecutionResult:
        remaining = deadline - time.monotonic()
        if self._closed.is_set():
            return ExecutionResult(status='cancelled')
        if remaining <= 0:
            return ExecutionResult(status='timeout')
        # The same-UID child can signal its worker. Enforce time independently
        # on the host too, with a bounded allowance for Docker transport.
        deadline = min(deadline, time.monotonic() + (20 if compile else 2) + .25)
        request = json.dumps({'argv': argv, 'stdin': stdin, 'timeout': min(20 if compile else 2, remaining), 'compile': compile}).encode() + b'\n'
        if len(request) > MESSAGE_LIMIT:
            raise ValueError('Runner input exceeds message limit')
        try:
            process = subprocess.Popen(
                ['docker', 'exec', '-i', container, 'python', '-I', '/opt/worker.py'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        except OSError:
            self._remove(container, self.deadline)
            return ExecutionResult(status='runner_error', stderr='Cannot start Docker worker')
        buffers = {'stdout': bytearray(), 'stderr': bytearray()}
        interrupted = None
        try:
            with selectors.DefaultSelector() as selector:
                for field in ('stdout', 'stderr'):
                    pipe = getattr(process, field)
                    os.set_blocking(pipe.fileno(), False)
                    selector.register(pipe, selectors.EVENT_READ, field)
                os.set_blocking(process.stdin.fileno(), False)
                selector.register(process.stdin, selectors.EVENT_WRITE, 'stdin')
                offset = 0
                while selector.get_map():
                    if self._closed.is_set():
                        interrupted = 'cancelled'
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        interrupted = 'timeout'
                        break
                    for key, _ in selector.select(min(.05, remaining)):
                        if key.data == 'stdin':
                            try:
                                offset += os.write(key.fd, request[offset:offset + 8192])
                            except BrokenPipeError:
                                offset = len(request)
                            if offset == len(request):
                                selector.unregister(key.fileobj)
                                key.fileobj.close()
                        else:
                            chunk = os.read(key.fd, 8192)
                            if not chunk:
                                selector.unregister(key.fileobj)
                            else:
                                buffers[key.data].extend(chunk)
                                if len(buffers[key.data]) > (MESSAGE_LIMIT if key.data == 'stdout' else 65536):
                                    interrupted = 'runner_error'
                                    break
                    if interrupted:
                        break
            if interrupted:
                self._remove(container, self.deadline)
                return ExecutionResult(status=interrupted)
            process.wait(timeout=max(.001, deadline - time.monotonic()))
            if process.returncode:
                self._remove(container, self.deadline)
                return ExecutionResult(status='cancelled' if self._closed.is_set() else 'runner_error', stderr='Docker worker exited unexpectedly')
            result = ExecutionResult.model_validate_json(bytes(buffers['stdout']))
            if result.status == 'runner_error':
                self._remove(container, self.deadline)
            return result
        except (ValueError, subprocess.TimeoutExpired):
            self._remove(container, self.deadline)
            return ExecutionResult(status='runner_error', stderr='Invalid or incomplete worker response')
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            for pipe in (process.stdin, process.stdout, process.stderr):
                pipe.close()

    def compile_cpp(self, source: str, deadline: float | None = None) -> Handle:
        deadline = deadline or time.monotonic() + 30
        if deadline <= time.monotonic():
            raise RunnerError("Compilation budget expired")
        with self._operation:
            directory = self._sources({'main.cpp': source})
            name = self._start('submitted', directory, compile=True, deadline=deadline)
            try:
                result = self._request(name, ('g++', '-std=gnu++17', '-O2', '-pipe', '/sources/main.cpp', '-o', '/work/program'), '', min(deadline, time.monotonic() + 20), compile=True)
                if result.status != 'ok':
                    raise CompilationError(result)
                # Docker's archive/cp endpoint cannot see this tmpfs on Desktop.
                # Export through a trusted, bounded reader; never run the binary here.
                reader = "import sys; f=open('/work/program','rb'); data=f.read(16777217); sys.exit(1) if len(data)>16777216 else sys.stdout.buffer.write(data)"
                try:
                    exported = subprocess.run(
                        ['docker', 'exec', name, 'python', '-I', '-c', reader],
                        capture_output=True, timeout=max(.001, min(10, deadline-time.monotonic())),
                    )
                except (OSError, subprocess.TimeoutExpired) as error:
                    raise RunnerError('Cannot export compiled program') from error
                if exported.returncode or not exported.stdout:
                    raise RunnerError('Compiled program is missing or exceeds 16 MiB')
                (directory / 'program').write_bytes(exported.stdout)
                (directory / 'program').chmod(0o555)
            finally:
                self._remove(name, deadline)
            runtime = self._start('submitted', directory, deadline=deadline)
            return Handle(runtime, self.run_id, ('/sources/program',), 'submitted', directory)

    def execute(self, handle: Handle, stdin: str, deadline: float) -> ExecutionResult:
        if handle.run_id != self.run_id:
            raise ValueError('Handle belongs to another run')
        with self._operation:
            if self._closed.is_set():
                return ExecutionResult(status='cancelled')
            if deadline <= time.monotonic():
                return ExecutionResult(status='timeout')
            with self._lock:
                present = handle.container in self._containers and handle.container not in self._poisoned
            if not present:
                handle.container = self._start(handle.role, handle.sources, deadline=deadline)
            return self._request(handle.container, handle.argv, stdin, deadline)

    def close(self, deadline: float | None = None):
        self._closed.set()
        with self._lock:
            names = tuple(self._containers)
        end = deadline if deadline is not None else time.monotonic() + 5
        if names:
            with ThreadPoolExecutor(max_workers=len(names)) as pool:
                futures = [pool.submit(self._remove, name, end) for name in names]
                for future in futures:
                    future.result()
        with self._lock:
            return not self._containers
