import concurrent.futures
import json
import subprocess
import time

import pytest


def make_runner(tmp_path):
    from app.runner import Runner

    return Runner(tmp_path)


def test_cpp_compiles_and_runs_with_codeforces_headers(tmp_path):
    runner = make_runner(tmp_path)
    try:
        handle = runner.compile_cpp('#include <bits/stdc++.h>\nint main(){long long a,b;std::cin>>a>>b;std::cout<<a+b<<"\\n";}')
        result = runner.execute(handle, '17 -5\n', time.monotonic() + 5)
        assert result.status == 'ok'
        assert result.stdout == '12\n'
        assert result.exit_code == 0
        assert runner.execute(handle, '4 9\n', time.monotonic() + 5).stdout == '13\n'
    finally:
        runner.close()


def test_compile_error_is_bounded_and_containers_are_removed(tmp_path):
    from app.runner import CompilationError

    runner = make_runner(tmp_path)
    try:
        with pytest.raises(CompilationError) as error:
            runner.compile_cpp('int main( {')
        assert 'error:' in error.value.result.stderr
        assert len(error.value.result.stderr.encode()) <= 65536
    finally:
        runner.close()
    assert not containers(runner.run_id)


def containers(run_id):
    return subprocess.check_output(
        ['docker', 'ps', '-aq', '--filter', f'label=counterexample.run={run_id}'], text=True
    ).strip()


@pytest.mark.parametrize('stream', ['stdout', 'stderr'])
def test_output_limit_stops_writer(tmp_path, stream):
    runner = make_runner(tmp_path)
    try:
        handle = runner.prepare('primary', {'main.py': f'import os\nwhile True: os.write({1 if stream == "stdout" else 2}, b"x"*8192)\n'})
        result = runner.execute(handle, '', time.monotonic() + 5)
        assert result.status == 'output_limit'
        assert len(getattr(result, stream).encode()) == 65536
        assert runner.execute(handle, '', time.monotonic() + 5).status == 'output_limit'
    finally:
        runner.close()


def test_timeout_kills_children_and_next_execution_is_fresh(tmp_path):
    runner = make_runner(tmp_path)
    source = '''import os,sys,time
if sys.stdin.read().strip() == 'hang':
    if os.fork() == 0:
        os.setsid()
        while True: time.sleep(1)
    while True: time.sleep(1)
else:
    print('fresh')
'''
    try:
        handle = runner.prepare('primary', {'main.py': source})
        start = time.monotonic()
        result = runner.execute(handle, 'hang', start + 5)
        assert result.status == 'timeout'
        assert time.monotonic() - start < 5
        assert runner.execute(handle, 'ok', time.monotonic() + 5).stdout == 'fresh\n'
        proc = subprocess.check_output(['docker', 'exec', handle.container, 'ps', '-eo', 'args'], text=True)
        assert '/sources/main.py' not in proc
    finally:
        runner.close()
    assert not containers(runner.run_id)


def test_background_child_is_removed_after_normal_exit(tmp_path):
    runner = make_runner(tmp_path)
    source = '''import os,time
if os.fork() == 0:
    os.setsid()
    os.close(1); os.close(2)
    while True: time.sleep(1)
print('done')
'''
    try:
        handle = runner.prepare('primary', {'main.py': source})
        assert runner.execute(handle, '', time.monotonic() + 5).stdout == 'done\n'
        proc = subprocess.check_output(['docker', 'exec', handle.container, 'ps', '-eo', 'args'], text=True)
        assert '/sources/main.py' not in proc
    finally:
        runner.close()


def test_isolation_blocks_network_host_secrets_and_other_roles(tmp_path, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'host-only-secret-test-value')
    runner = make_runner(tmp_path)
    candidate = 'candidate-private-marker'
    source = '''import json,os,socket
from pathlib import Path
s=socket.socket();s.settimeout(.3)
try:
    s.connect(('1.1.1.1',443)); connected=True
except OSError: connected=False
try:
    Path('/root-write-test').write_text('x'); writable=True
except OSError: writable=False
print(json.dumps({'uid':os.getuid(),'network':connected,'root_writable':writable,
 'key':os.getenv('GEMINI_API_KEY'),'socket':Path('/var/run/docker.sock').exists(),
 'home':Path('/Users/andreyryzhanskiy').exists(),'candidate':Path('/sources/private.cpp').exists()}))
'''
    try:
        runner.prepare('submitted', {'private.cpp': candidate, 'main.py': 'print(1)'})
        handle = runner.prepare('primary', {'main.py': source})
        result = runner.execute(handle, '', time.monotonic() + 5)
        assert result.status == 'ok'
        assert json.loads(result.stdout) == {
            'uid': 65534, 'network': False, 'root_writable': False,
            'key': None, 'socket': False, 'home': False, 'candidate': False,
        }
    finally:
        runner.close()


def test_container_enforces_memory_cpu_and_pid_limits(tmp_path):
    runner = make_runner(tmp_path)
    try:
        handle = runner.prepare('confirmation', {'main.py': 'print(1)'})
        config = json.loads(subprocess.check_output(['docker', 'inspect', handle.container], text=True))[0]
        host = config['HostConfig']
        assert host['Memory'] == 536870912
        assert host['NanoCpus'] == 1000000000
        assert host['PidsLimit'] == 128
        assert host['ReadonlyRootfs']
        assert host['NetworkMode'] == 'none'
        assert host['CapDrop'] == ['ALL']
        assert 'no-new-privileges' in host['SecurityOpt']
        assert host['LogConfig']['Type'] == 'none'
        assert config['Config']['User'] == '65534:65534'
        assert all(m['Destination'] == '/sources' and not m['RW'] for m in config['Mounts'] if m['Type'] == 'bind')
    finally:
        runner.close()


def test_close_cancels_active_execution(tmp_path):
    runner = make_runner(tmp_path)
    handle = runner.prepare('submitted', {'main.py': 'import time\ntime.sleep(30)'})
    try:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(runner.execute, handle, '', time.monotonic() + 30)
            time.sleep(.25)
            runner.close()
            assert future.result(timeout=5).status == 'cancelled'
    finally:
        runner.close()
    assert not containers(runner.run_id)


def test_expired_deadline_never_runs_program(tmp_path):
    runner = make_runner(tmp_path)
    try:
        handle = runner.prepare('submitted', {'main.py': "print('should not execute')"})
        result = runner.execute(handle, '', time.monotonic() - 1)
        assert result.status == 'timeout'
        assert result.stdout == ''
    finally:
        runner.close()


@pytest.mark.parametrize('sources', [{'../escape.py': 'print(1)'}, {'main.py': 'x' * 262145}])
def test_rejects_unsafe_or_oversized_sources(tmp_path, sources):
    runner = make_runner(tmp_path)
    try:
        with pytest.raises(ValueError):
            runner.prepare('primary', sources)
        assert not containers(runner.run_id)
    finally:
        runner.close()


def test_crash_has_exit_status(tmp_path):
    runner = make_runner(tmp_path)
    try:
        handle = runner.prepare('submitted', {'main.py': 'import os\nos._exit(7)'})
        result = runner.execute(handle, '', time.monotonic() + 5)
        assert result.status == 'runtime_error'
        assert result.exit_code == 7
    finally:
        runner.close()


def test_unprivileged_workspaces_are_writable(tmp_path):
    runner = make_runner(tmp_path)
    try:
        handle = runner.prepare('primary', {'main.py': "from pathlib import Path\nPath('/work/file').write_text('work')\nPath('/tmp/file').write_text('tmp')\nprint('written')"})
        result = runner.execute(handle, '', time.monotonic() + 5)
        assert result.status == 'ok', result.stderr
        assert result.stdout == 'written\n'
    finally:
        runner.close()


def test_close_cancels_compilation_and_removes_compiler(tmp_path):
    from app.runner import RunnerError

    runner = make_runner(tmp_path)
    source = '#include <bits/stdc++.h>\nconstexpr unsigned long f(unsigned n){return n<2?n:f(n-1)+f(n-2);}\nconstexpr auto x=f(45);\nint main(){return x;}'
    try:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(runner.compile_cpp, source)
            until = time.monotonic() + 5
            compiler_seen = False
            while time.monotonic() < until and not future.done():
                name = containers(runner.run_id)
                if name:
                    processes = subprocess.run(['docker', 'exec', name, 'ps', '-eo', 'args'], capture_output=True, text=True)
                    if 'cc1plus' in processes.stdout:
                        compiler_seen = True
                        break
                time.sleep(.02)
            assert compiler_seen, 'Did not observe the active GNU compiler'
            runner.close()
            with pytest.raises(RunnerError):
                future.result(timeout=5)
    finally:
        runner.close()
    assert not containers(runner.run_id)


def test_runtime_memory_limit_stops_large_allocation(tmp_path):
    runner = make_runner(tmp_path)
    try:
        handle = runner.prepare('submitted', {'main.py': 'data=bytearray(700*1024*1024)\nprint("too much")'})
        result = runner.execute(handle, '', time.monotonic() + 5)
        assert result.status == 'runtime_error'
        assert result.exit_code != 0
        assert result.stdout == ''
    finally:
        runner.close()


def test_host_timeout_survives_suspended_worker(tmp_path):
    runner = make_runner(tmp_path)
    try:
        handle = runner.prepare('submitted', {'main.py': 'import os,signal,time\nos.kill(os.getppid(),signal.SIGSTOP)\ntime.sleep(30)'})
        started = time.monotonic()
        result = runner.execute(handle, '', started + 8)
        assert result.status == 'timeout'
        assert time.monotonic() - started < 3.5
        assert not containers(runner.run_id)
    finally:
        runner.close()


def test_child_cannot_access_worker_protocol_descriptor(tmp_path):
    runner = make_runner(tmp_path)
    source = '''import os
try:
    fd=os.open(f'/proc/{os.getppid()}/fd/1',os.O_WRONLY)
except PermissionError:
    print('blocked')
else:
    os.close(fd); print('accessible')
'''
    try:
        handle = runner.prepare('submitted', {'main.py': source})
        result = runner.execute(handle, '', time.monotonic() + 5)
        assert result.status == 'ok', result.stderr
        assert result.stdout == 'blocked\n'
    finally:
        runner.close()


def test_cleanup_removes_forking_detached_descendants(tmp_path):
    runner = make_runner(tmp_path)
    source = '''import os,time
if os.fork() == 0:
    os.setsid()
    for i in range(12):
        if os.fork() == 0:
            os.setsid(); time.sleep(30); os._exit(0)
        time.sleep(.003)
    time.sleep(30)
else:
    print('parent finished')
'''
    try:
        handle = runner.prepare('primary', {'main.py': source})
        assert runner.execute(handle, '', time.monotonic() + 5).status == 'timeout'
        processes = subprocess.run(['docker', 'exec', handle.container, 'ps', '-eo', 'args'], capture_output=True, text=True)
        assert '/sources/main.py' not in processes.stdout
    finally:
        runner.close()


def test_expired_lifecycle_deadline_never_starts_container(tmp_path,monkeypatch):
    import app.runner as module
    runner=module.Runner(tmp_path,deadline=time.monotonic()-1)
    calls=[]
    monkeypatch.setattr(module,'docker',lambda *args,**kwargs:calls.append(args))
    with pytest.raises(module.RunnerError,match='budget'):
        runner.prepare('primary',{'main.py':'print(5)'})
    assert not calls
    assert runner.close()
