import contextlib
import json
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
import httpx

from app.contracts import CounterexampleResult, RunRequest, RunSnapshot
from app.ingestion import import_html
from app.runner import Runner, readiness
from app.search import search

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
RUNS_ROOT = ROOT / '.runs'
app = FastAPI(title='Counterexample Lab', docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]'])
_jobs = {}
_lock = threading.Lock()


@app.middleware('http')
async def local_origin(request: Request, call_next):
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        origin = request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail': 'Writes must originate from this local application.'}, status_code=403)
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': 'Cross-site writes are rejected.'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'"
    return response


def provider_readiness():
    name = os.getenv('MODEL_PROVIDER', 'lmstudio')
    info = {'name': name, 'configured': False, 'reachable': False, 'generation_verified': False}
    if name == 'gemini':
        info.update(configured=bool(os.getenv('GEMINI_API_KEY')), model=os.getenv('GEMINI_MODEL', 'gemini-3.8-flash'))
        # Presence of a credential is not proof of generation availability.
        info['reachable'] = info['configured']
    elif name == 'lmstudio':
        model = os.getenv('LMSTUDIO_MODEL', 'counterexample-local')
        base = os.getenv('LMSTUDIO_BASE_URL', 'http://127.0.0.1:1234/v1').rstrip('/')
        info.update(configured=True, model=model)
        endpoint = urlsplit(base)
        if endpoint.scheme == 'http' and endpoint.hostname in ('127.0.0.1','localhost','::1'):
            try:
                response = httpx.get(base + '/models', timeout=2, trust_env=False)
                response.raise_for_status()
                info['reachable'] = any(item['id'] == model for item in response.json()['data'])
            except (httpx.HTTPError, ValueError, KeyError, TypeError):
                pass
    return info


@app.get('/api/health')
def health():
    return {'runner': readiness(), 'provider': provider_readiness()}


@app.post('/api/import')
async def ingest(file: UploadFile):
    try:
        data = await file.read(5 * 1024 * 1024 + 1)
        return import_html(data)
    except (ValueError, UnicodeError) as error:
        raise HTTPException(422, str(error)) from error
    finally:
        await file.close()


def _work(id, payload, runner, cancel):
    def progress(stage, counts, elapsed):
        with _lock:
            _jobs[id]['snapshot'].stage = stage
            _jobs[id]['snapshot'].counts = counts
            _jobs[id]['snapshot'].elapsed = elapsed
    started = time.monotonic()
    budget_end = runner.deadline
    try:
        result = search(payload.problem, payload.source, seed=payload.seed,
            deadline=runner.deadline, cancel=cancel, on_progress=progress, runner=runner)
    except Exception:
        result = CounterexampleResult(outcome='runner_failure', message='Unexpected run failure. Evidence was not corroborated.', seed=payload.seed, elapsed=time.monotonic()-started)
    finally:
        runner.close(deadline=budget_end)
    with contextlib.suppress(OSError):
        target = runner.root / 'result.json'
        target.write_text(result.model_dump_json(indent=2))
        target.chmod(0o600)
    with _lock:
        _jobs[id]['snapshot'] = RunSnapshot(id=id, stage='finished', terminal=True, elapsed=result.elapsed, counts=result.counts, result=result)


@app.post('/api/runs', status_code=202)
def create_run(payload: RunRequest):
    with _lock:
        if any(not job['snapshot'].terminal for job in _jobs.values()):
            raise HTTPException(409, 'A run is already active. Cancel it or wait for completion.')
    runner_info = readiness()
    provider_info = provider_readiness()
    if not runner_info.get('ready') or not provider_info.get('configured') or not provider_info.get('reachable'):
        raise HTTPException(503, 'Runner or selected model is unavailable. Check readiness.')
    with _lock:
        if any(not job['snapshot'].terminal for job in _jobs.values()):
            raise HTTPException(409, 'A run is already active.')
        # Keep a bounded in-memory history. Local artifacts remain on disk.
        while len(_jobs) >= 32:
            del _jobs[next(iter(_jobs))]
        id = uuid.uuid4().hex
        runner = Runner(RUNS_ROOT, deadline=time.monotonic()+180)
        cancel = threading.Event()
        snapshot = RunSnapshot(id=id)
        _jobs[id] = {'snapshot': snapshot, 'runner': runner, 'cancel': cancel}
        path = runner.root / 'request.json'
        path.write_text(payload.model_dump_json(indent=2)); path.chmod(0o600)
        threading.Thread(target=_work, args=(id, payload, runner, cancel), daemon=True).start()
        return snapshot


@app.get('/api/runs/{id}')
def get_run(id: str):
    with _lock:
        if id not in _jobs:
            raise HTTPException(404, 'Unknown run ID.')
        return _jobs[id]['snapshot'].model_copy(deep=True)


@app.post('/api/runs/{id}/cancel')
def cancel_run(id: str):
    with _lock:
        if id not in _jobs:
            raise HTTPException(404, 'Unknown run ID.')
        job = _jobs[id]
        if not job['snapshot'].terminal:
            job['cancel'].set()
            threading.Thread(target=job['runner'].close, daemon=True).start()
        return {'id': id, 'cancellation_requested': True}


app.mount('/static', StaticFiles(directory=ROOT / 'app' / 'static'), name='static')


@app.get('/')
def index():
    return FileResponse(ROOT / 'app' / 'static' / 'index.html')
