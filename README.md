# Counterexample Lab

A local browser tool that searches for counterexamples to C++17 competitive-programming solutions. Import a saved Codeforces HTML page or paste the statement, add its samples, then paste or upload your solution. AI writes an independent small-case testing module; restricted Docker containers execute every reference and submission. A second independent reference checks an observed output disagreement before it is labeled corroborated.

Built solo by [And850](https://github.com/And850) for EvoHacks, **AI for Automation**. Core implementation began after kickoff. No paid service is required for the local workflow.

## Run locally

Requires Python 3.12+, Docker Desktop, and LM Studio. Tested on an M1 Pro Mac with 16 GB RAM, Python 3.14.6, GNU g++ 12, and an ARM64 runner. LM Studio serves the existing Qwen3.5-9B MLX 4-bit model with an 8192-token context.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p .runs/buildx
BUILDX_CONFIG="$PWD/.runs/buildx" docker build -t counterexample-runner:step1 runner
```

Copy `.env.example` to `.env` only if `.env` does not already exist. Preserve existing credentials. Select the local provider:

```dotenv
MODEL_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
LMSTUDIO_MODEL=counterexample-local
LMSTUDIO_API=native
```

In LM Studio, download/load `qwen/qwen3.5-9b`, or load an already downloaded model with its CLI:

```sh
lms load qwen/qwen3.5-9b --context-length 8192 --identifier counterexample-local -y
lms server start --port 1234 --bind 127.0.0.1
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --env-file .env
```

Open [Counterexample Lab](http://127.0.0.1:8001). Port 8001 avoids another service already running on the development machine; any free local port works. Bind to loopback only. The app preserves editable inputs when a run fails.

The [native LM Studio API](https://lmstudio.ai/docs/developer/rest/chat) supports reasoning disabled. The module schema is supplied in the prompt and enforced locally by Pydantic; native generation is not decoder-constrained. `LMSTUDIO_API=openai` retains the schema-constrained compatibility endpoint, whose Qwen reasoning routing produced incomplete modules during testing. Optional `MODEL_PROVIDER=gemini` uses Google GenAI JSON-schema responses, but live Gemini generation has **not** passed on this machine. The app never changes provider or activates billing automatically.

## Workflow and evidence

1. Save the Codeforces problem page as HTML. Import it and review title, statement, constraints, warnings, and samples. Embedded scripts, styles and unrelated page content are discarded; raw TeX is preserved as text.
2. Paste or upload a `.cpp` file. Add at least one complete sample and choose a seed.
3. Run the search. Stages and generated/valid/tested/invalid/timeout counts appear while cancellation remains available.
4. Inspect the failing input, reference output, actual output, reference implementations and SHA-256 hashes. Download the complete result as JSON.

Primary preparation checks every sample, parser/render round trips and all generator modes. Search tries samples, up to 256 tiny exhaustive cases, then alternating seeded random and adversarial cases. Exhaustive generation yields after 20 seconds, 30% of remaining first-search time, or eight consecutive duplicates so a weak generator cannot consume the entire search budget. Integer output comparison ignores whitespace only. On a mismatch, a fresh model request sees only statement and samples; both validators and references must agree. Reduction accepts strictly smaller inputs only after fresh reference and candidate executions.

Outcomes distinguish `corroborated_counterexample`, `unconfirmed_disagreement`, `runtime_finding`, `inconclusive`, preparation/provider/runner failures, and cancellation. A run with no disagreement is **inconclusive**, never a correctness claim. AI references can share a mistake; corroboration is evidence rather than proof. The reducer does not establish global minimality. Explanations are labeled AI-generated and use executed evidence.

Limits: 180 seconds per run, including up to five seconds reserved for concurrent cleanup; 120 seconds to first disagreement; 45 seconds per model request; four model calls; one repair shared across both references; at most 10,000 generated cases. Candidate/reference execution is limited to two seconds with 64 KiB output per stream. Confirmation or explanation failures retain useful evidence. Cancellation during reduction retains the last corroborated input.

## Scope

This version supports deterministic stdin/stdout C++17 programs with a unique sequence of integer output tokens and small inputs suitable for brute force. Java, PDF import, custom checkers, floating-point output and multiple valid outputs are outside this version. Large-input bugs and difficult constraints may be missed. HTML pages with missing samples or image-only content require manual review.

Each role runs in a separate nonroot Docker container: no network, read-only root and role sources, dropped capabilities, no-new-privileges, one CPU, 128 PIDs, 512 MiB runtime memory, bounded tmpfs. Compilation has a 20-second ceiling and 1 GiB memory. Generated code is never imported or executed on the host. Only role sources and the compiled artifact are mounted; `.env` is excluded. This is a local hackathon tool, not a hosted multi-user execution service.

Run artifacts are stored under ignored `.runs/<uuid>/`, including source modules and final evidence. They are local and may contain your inputs. Delete completed directories manually when no run uses them. Requests are not resumed after server restart. Keep `.env` private; the public repository contains only synthetic HTML fixtures.

## Verification

```sh
.venv/bin/python -m pytest -q
# Offline interface checks:
mkdir -p .runs/dom-check
cp tests/ui/package.json tests/ui/package-lock.json .runs/dom-check/
npm ci --prefix .runs/dom-check --cache .runs/npm-cache
node tests/ui/check.cjs
.venv/bin/python -m app.smoke
.venv/bin/python -m benchmarks.evaluate
docker ps -a --filter label=counterexample.run
```

Ordinary pytest and DOM tests use deterministic fixtures and do not call a model. Docker tests are mandatory and do not silently skip an unavailable daemon/image. DOM checks simulate interface interactions without opening a browser or making network requests. **Real browser/visual verification was blocked by the session's browser permission policy and remains outstanding.**

`app.smoke` explicitly invokes the selected live provider and tests an intentionally incorrect absolute-sum algorithm. One native Qwen run found input `0 -100`, expected `-100`, actual `100`, corroborated in 55.9 seconds. Fresh generation can fail or produce different cases.

[Fixed evaluation cases](benchmarks/cases.json) include sum, nonempty maximum interval, 0/1 knapsack, distinct counting, and the supplied cyclic-array snowman problem, each with correct and incorrect controls. [Recorded evaluation](benchmarks/results.json) reports every attempt, including failures. Independently authored exhaustive definitions verify sample answers and observed reference outputs. Evaluation is in progress; the three-of-five target is not yet established.

See [implementation progress](docs/superpowers/progress.md), [design](docs/superpowers/specs/2026-10-10-counterexample-lab-design.md), and [plan](docs/superpowers/plans/2026-10-10-counterexample-lab.md).

## Submission artifacts

[Devpost draft](submission/devpost-description.md) and [two-minute narration](submission/video-script.md) are prepared. The local `submission/evidence-walkthrough.mp4` is a silent 120-second slide walkthrough of the corroborated live run, not a browser recording. To render it from `.runs/live-smoke-result.json`, install `submission/requirements.txt` and run `python -m submission.render_demo`; it requires FFmpeg and the macOS Arial font used on the development machine. The video is excluded from Git. No Devpost submission has been made automatically.
