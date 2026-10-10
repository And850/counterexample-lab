# Counterexample Lab Implementation Plan

**Task 1 completion update (October 10):** The isolated runner, Python environment, minimal server, local-model smoke check, and 28 passing tests are complete. See [verification evidence](../task-1-status.md). LM Studio is the authorized zero-cost fallback and GitHub is the requested delivery repository. Gemini generation remains unverified; later provider work must support the selected local model and validate its known `reasoning_content` JSON routing. Core implementation began after kickoff. Tasks 2–4 are implemented; Task 5 has API/offline DOM verification with real-browser permission blocked; Task 6 evaluation is in progress.

> For agentic workers: use superpowers:executing-plans to implement this plan task by task in the current session. Do not delegate unless separately authorized. Complete the verification associated with each task before proceeding.

**Goal:** Turn a Codeforces statement and C++ submission into a small, reproducible counterexample using AI-generated brute-force testing, through a local browser interface.

**Architecture:** A local FastAPI process serves a buildless browser interface and orchestrates bounded background runs. A free Gemini API produces structured testing code; separate restricted Docker roles execute submitted and generated code. The host owns deadlines, comparison, evidence, and result classification.

**Tech stack:** Python 3.12+, FastAPI/Uvicorn, Pydantic, Beautiful Soup, Google GenAI SDK, HTML/CSS/JavaScript, Docker with GNU C++17, pytest, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-10-counterexample-lab-design.md`. Read this before implementation; this plan and the spec jointly define the work.

## Global constraints

- Zero spending; no billing activation, paid model fallback, or paid hosting.
- Local browser application on `127.0.0.1:8000`, one active run, 180 seconds per run, at most four model calls.
- C++17, integer/array problems, unique integer-token outputs; HTML/text and `.cpp`/text input only.
- Never execute submitted/generated code directly on the host; no secrets or Docker socket inside runners.
- No result claims universal correctness, global minimality, or proof based on generated-reference agreement.
- Implement core code only within the hackathon window. Deadline: October 11, 2026, 20:59 Europe/Madrid.
- Working repository name is `And850/counterexample-lab`; dependencies, image, and provider access are checked before engine implementation.

## Review focus

1. Saved HTML silently loses sample lines or inequalities: pin exact imported text and sample tests in Task 2.
2. A plausible but wrong reference passes samples: disagreement between references must remain unconfirmed in Task 4.
3. Reduction violates coupled constraints: both validators must accept every retained case in Task 4.
4. Cancellation leaves processes or containers running: verify forced cleanup during compilation, execution, and model calls in Tasks 1 and 5.
5. A quota failure or timeout looks like success: preserve evidence and classify incomplete work explicitly in Tasks 3–5.

## Responsibility boundaries

Keep `app/` organized around ingestion, typed contracts, provider, runner, search, and HTTP orchestration. Keep static browser assets together, container worker/image definitions under `runner/`, and deterministic fixtures/tests under `tests/`. Host modules must not import generated modules. Use one shared set of Pydantic contracts and one monotonic deadline utility.

## Task 1 — Establish prerequisites and the isolated runner (about 2 hours)

**Deliverable:** A known C++ program compiles and runs inside the intended isolation boundary, with repeatable error handling.

**Consumes:** Docker installation, available free API account, existing empty project folder.
**Produces:** `Runner.prepare(role, sources)`, `Runner.compile_cpp(source)`, `Runner.execute(handle, stdin, deadline) -> ExecutionResult`, and `Runner.close()`; a readiness check and pinned dependencies.

- [x] Resolve the Docker signal-9 issue with read-only diagnostics first. Verify server availability, ARM64 image builds, and process/resource controls. If Docker cannot run, report the prerequisite failure; do not replace it with host execution.
- [x] Configure the authorized zero-cost local LM Studio fallback and pass a structured-output smoke check. Preserve optional Gemini configuration; its generation readiness remains explicitly unverified. No paid fallback.
- [x] Initialize the local Git repository, add ignores for virtual environments, `.env`, `.runs`, caches, and raw uploaded pages, then create the planned public repository under And850. Never commit credentials or personal saved-page content.
- [x] Add the Python environment, minimal server skeleton, and runner image in the same task. Use GNU g++ in the image so Codeforces headers work on this Mac.
- [x] Write runner integration tests for echo/sum, compilation failure, `bits/stdc++.h`, timeout, output overflow, child-process cleanup, blocked networking, and absence of host secrets/files.
- [x] Implement separate role containers and bounded trusted worker messages. Apply the exact isolation, memory, process, output, and timeout settings from the spec; fresh child process per execution.
- [x] Run `python -m pytest tests/test_runner.py -q` (19 passed) and the full suite (28 passed); publish directly to GitHub only after passing verification. Docker-dependent tests were not skipped.

## Task 2 — Import statements and define shared contracts (about 1.5 hours)

**Deliverable:** A normalized, editable problem document with samples; no AI call required.

**Consumes:** HTML bytes or pasted text.
**Produces:** `import_html(data: bytes) -> ProblemInput`; Pydantic models for the problem, generated bundle, execution result, progress, and final result.

- [x] Add a minimal synthetic fixture matching the supplied Codeforces structure, including Russian text, raw TeX, list items, nested sample divs, scripts, and unrelated page text. Test the real supplied file locally without copying the full personal webpage into Git.
- [x] Write tests asserting all 17 input lines and four output lines survive, the strict inequality and constraints remain intact, and scripts are never executed or rendered.
- [x] Cover `<br>` samples, original versus rendered math representations, missing `.problem-statement`, undecodable input, oversized input, and incomplete sample pairs.
- [x] Implement extraction, warnings, decoding, size limits, and schema validation. Keep pasted sample inputs explicit and editable.
- [x] Define the module/worker interfaces exactly as described in the spec, including bounded case lists and JSON-serializable structured cases.
- [x] Run `python -m pytest tests/test_ingestion.py tests/test_contracts.py -q`; review the supplied page's extracted preview; commit the passing importer/contracts.

## Task 3 — Generate and validate a testing bundle (about 2 hours)

**Deliverable:** The statement yields a sample-checked executable brute-force harness, or an explicit preparation error.

**Consumes:** `ProblemInput`, the runner, and an absolute monotonic deadline.
**Produces:** `Provider.generate_primary(problem, deadline) -> GeneratedBundle`, `Provider.generate_confirmation(problem, deadline)`, `Provider.explain(evidence, deadline)`, and a checked harness handle.

- [x] Write mocked-provider tests for valid structured JSON, schema failures, truncated responses, empty code, sample mismatch, syntax errors, request timeout, missing credentials, and rate limiting.
- [x] Use the Google GenAI SDK with JSON-schema structured responses and local Pydantic validation. The primary prompt receives only statement/samples and demands exhaustive small-input reasoning, valid deterministic generators, and structure-aware reductions.
- [x] Compile/check generated modules only in their runner roles. Check every sample and parser round trip before search. Permit one repair across the complete run; preserve the failure if repair is exhausted.
- [x] Implement four-call and 45-second-per-call ceilings within the shared deadline. Stop on quota exhaustion; no automatic paid or provider fallback. Never log authorization headers.
- [x] Define a new confirmation request with no prior conversation, candidate code, primary implementation, or observed answers. Require its own input validator and general reference solver.
- [x] Add an explicit live smoke command for developers; ordinary automated tests remain offline and deterministic. Record only nonsecret evidence from the live prerequisite check.
- [x] Run `python -m pytest tests/test_provider.py tests/test_preparation.py -q`; commit when passing.

## Task 4 — Search, corroborate, and reduce (about 3 hours)

**Deliverable:** A repeatable failing case with defensible result semantics.

**Consumes:** A prepared primary harness, compiled candidate handle, provider, seed, and deadline.
**Produces:** `search(problem, candidate, seed, deadline, cancel, on_progress) -> CounterexampleResult`, including evidence and failure classification.

- [x] Use hand-authored fixture bundles to write deterministic tests before connecting live AI. Include a correct candidate, a greedy algorithm failure, invalid generator outputs, and a wrong primary oracle that agrees with samples.
- [x] Implement sample-first search, up to 256 tiny exhaustive candidates, alternating seeded random/adversarial candidates, deduplication, and the 10,000-candidate/120-second first-disagreement limits. Count invalid and timed-out cases separately.
- [x] Parse output as signed arbitrary-precision integer tokens, ignoring whitespace only. Test large integers, missing/extra tokens, noninteger output, crashes, and timeouts.
- [x] On disagreement, execute the separately generated reference against samples and the case. Require both validators and both references to agree before marking corroborated. Keep an unconfirmed result if any check fails or cannot finish.
- [x] Implement reduction with the spec's strict decreasing complexity measure and fresh executions of the candidate and both references. Test coupled array lengths, aggregate constraints, invalid reductions, duplicate proposals, and interruption mid-reduction.
- [x] Keep the last corroborated case when the deadline expires. Generate an explanation only from executed evidence and only if the remaining call/time budget permits; return useful evidence when explanation fails.
- [x] Assert that a correct fixture solution yields only an inconclusive outcome, never an assertion of correctness; an oracle disagreement must never be called a corroborated counterexample.
- [x] Run `python -m pytest tests/test_search.py tests/test_reduction.py -q`; commit the engine after passing.

**October 10 verification note:** Native LM Studio JSON is validated locally rather than decoder-constrained. The engine yields exhaustive search after bounded time or repeated cases to reserve time for random/adversarial modes. Container lifecycle deadlines include a reserved cleanup interval. See progress for evidence and verification gaps.

## Task 5 — Browser workflow and job lifecycle (about 2.5 hours)

**Deliverable:** The full input-to-result flow is usable through the local browser.

**Consumes:** Ingestion, validated contracts, runner, provider, and search engine.
**Produces:** The five HTTP routes defined in the spec and the buildless interface.

- [x] Write API tests for import, run creation, one-job concurrency, unknown IDs, cancellation, readiness failure, invalid samples, and safe error responses.
- [x] Add a single in-process asynchronous job registry; offload blocking subprocess work so polling/cancellation stay responsive. Persist bounded artifacts under `.runs/<uuid>/`; no database or resume protocol.
- [x] Serve input panels, sample editors, readiness status, stage/count progress, Cancel, and result details. `.cpp` upload fills the editable code field. Use text rendering, not HTML insertion, for all uploaded/model content.
- [x] Poll once per second and stop polling terminal jobs. Preserve entered inputs when a run fails. Enforce loopback hosting, local Host validation, and same-origin writes.
- [ ] Add browser tests for both upload and paste flows, keyboard controls, narrow layout, cancellation, compile errors, unconfirmed results, quota errors, and a successful fixture run. Clearly mark fixture-backed development mode; live demonstration uses the real provider.
- [ ] Run the full pytest suite and Playwright journey. Verify no containers remain after success, failure, or cancellation; commit the working interface.


## Task 6 — Evaluation and submission package (about 2 hours, then buffer)

**Deliverable:** A reproducible public project and an evidence-based hackathon demonstration.

- [ ] Prepare five fixed problems with one reviewed correct and one incorrect C++ solution each. Include the uploaded cyclic-array problem; verify its sample answers through direct enumeration rather than trusting generated prose.
- [ ] Run all ten solutions through the real workflow with fixed seeds. Record model ID, API errors, tests, elapsed time, outcome, and whether the reduced case agrees with independently reviewed ground truth.
- [ ] Require at least three of five incorrect candidates to produce corroborated cases within 180 seconds and zero false corroborated cases among correct controls. If the gate fails, improve reliability or report the narrower demonstrated coverage; do not hide failures or add features.
- [ ] Run the regression and browser suites after fixes. Check a fresh setup using the documented image build and local launch commands.
- [ ] Finish README setup, architecture explanation, supported scope, free API configuration, limitations, benchmark table, and secret-free public source. Push verified commits to And850/counterexample-lab.
- [ ] Prepare the Devpost description and a 2–3 minute video script covering the original pain, a real successful run, reduced input, expected/actual results, and code walkthrough. Record the demo and supply local setup instructions as the access route.
- [ ] Target submission readiness by October 11 at 19:30 Madrid time, ahead of the strict 20:59 deadline. Leave remaining time for upload and a final submission check.

## Delivery order and stop conditions

The estimates total about 13 hours of focused work, excluding account/Docker troubleshooting, download time, breaks, and submission delays. Complete the runner/API prerequisites first, then a headless end-to-end search before polishing the interface. If time becomes constrained, simplify visual styling and explanation prose; retain HTML import, input validation, execution isolation, honest outcomes, and a reproducible demo. PDF, Java, hosted execution, and multiple-output checkers remain outside this plan.

No implementation has been performed by writing these documents. Docker operation, API access, timing, and benchmark targets remain unverified until the specified milestones run.
