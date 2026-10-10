# Counterexample Lab

Local AI-assisted counterexample search for Codeforces C++ submissions. The hackathon MVP is in development. **Step 1 provides the isolated C++/Python runner, dependency lock, model smoke check, and health endpoint.** The HTML importer, search engine, and browser interface are not implemented yet.

## Setup

Requirements: Python 3.12+, Docker Desktop running, and LM Studio with the downloaded Qwen3.5-9B model. Development has been tested on an M1 Pro Mac with Python 3.14.6 and an ARM64 Python 3.12 runner image.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
BUILDX_CONFIG="$PWD/.runs/buildx" docker build -t counterexample-runner:step1 runner
```

The image builds GNU g++ 12 for `-std=gnu++17 -O2 -pipe`, including `bits/stdc++.h`. The base image digest is pinned; Debian package updates are resolved when building. The build context is only `runner/`, so `.env` and uploaded content are not sent to Docker's build service.

Copy `.env.example` to `.env` only if `.env` does not already exist. Keep an existing API key; never commit it. Settings:

```dotenv
MODEL_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
LMSTUDIO_MODEL=counterexample-local
```

Load and serve the existing model:

```sh
lms load qwen/qwen3.5-9b --context-length 8192 --identifier counterexample-local -y
lms server start --port 1234 --bind 127.0.0.1
.venv/bin/python -m app.readiness --live
```

This smoke check makes one local request, checks its JSON answer, and reports its response field. The installed LM Studio/Qwen combination currently puts schema-constrained JSON in `reasoning_content` instead of `content`; the smoke command accepts that field only when the complete result parses and matches the expected typed answer. A normal content-only client fails. This does not establish reference-solver quality. No automatic hosted or paid fallback is configured. Optional Gemini settings are retained, but its generation readiness has not passed.

Start the minimal server:

```sh
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file .env
```

Open [the health endpoint](http://127.0.0.1:8000/api/health). It checks the Docker daemon and image and reports provider configuration without exposing keys. `generation_verified` remains false in this polling endpoint; use the explicit smoke command for live evidence. There is no browser workflow yet.

## Runner verification

```sh
.venv/bin/python -m pytest tests/test_runner.py -q
.venv/bin/python -m pytest -q
docker ps -a --filter label=counterexample.run
```

Docker integration tests are mandatory and never skipped if the daemon/image is absent. They cover C++ compilation and errors, fresh execution, timeout and output caps, cleanup of detached child processes, cancellation during compilation/execution, blocked networking, unprivileged execution, separate role sources, host-secret exclusion, read-only root filesystems, and memory/CPU/PID settings.

Each run owns separate submitted, primary, and confirmation containers. Only that role's sources/artifact are mounted read-only. Compilation uses 1 GiB and a 20-second limit; runtime uses 512 MiB, one CPU, 128 PIDs, a two-second execution limit, and 64 KiB captured output per stream. The worker uses bounded JSON messages; compiled artifacts are exported through a trusted bounded reader and are never executed on the host. `Runner.close()` force-removes the run's containers. It must be called in a `finally` block.

Runtime artifacts live under ignored `.runs/`; remove completed run directories manually when no run is using them. Keep the build cache if rebuilding. This local Docker boundary is for the hackathon workflow, not a hosted multi-user execution service.

See the [implementation plan](docs/superpowers/plans/2026-10-10-counterexample-lab.md) and [task evidence](docs/superpowers/task-1-status.md) for current progress.
