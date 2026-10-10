# Counterexample Lab — MVP design

**Step 1 amendment (October 10):** Docker runner implementation and its acceptance checks pass. The user authorized local LM Studio/Qwen3.5-9B as a zero-cost fallback after Gemini generation timed out. Local schema generation passes, with JSON routed through `reasoning_content`; actual reference-code generation remains untested. Later provider work must support the selected local model. The Gemini-specific design below remains conditional on eligible access and verified free quota. See [Task 1 evidence](../task-1-status.md). Deliver source directly to `And850/counterexample-lab` as the user requested.

## Purpose and agreed scope

Build a zero-cost, local browser tool for competitive programmers who have a Codeforces problem statement and a plausible but incorrect C++ algorithm, without a trusted solution to compare against. Automate writing a small-input brute-force reference, generating tests, comparing outputs, and reducing a disagreement to an understandable input.

The user is a solo hackathon participant with six years of competitive programming experience. The development/demo machine is an Apple M1 Pro MacBook Pro with 16 GB RAM. GitHub CLI authentication as And850 was verified. The workspace was empty before these planning documents.

Supported inputs are pasted statement text or a saved Codeforces `.html`/`.htm` file, and pasted C++ or a `.cpp` file. Support integer/array problems with a unique sequence of integer output tokens and standard input/output, including multiple test cases. Preserve Russian and English statements. Results and application controls are in English.

Exclude Java, PDF/OCR, URL fetching, interactive problems, floating-point judging, multiple-valid-answer checkers, automatic solution fixes, accounts, public code execution, and cloud deployment. Do not add these before the core workflow and submission materials are complete.

## Defaults selected during planning

- Working product name: Counterexample Lab; planned repository: And850/counterexample-lab.
- Local-only application, served on `127.0.0.1:8000`; one active run.
- Three-minute total run budget, including AI, compilation, testing, confirmation, and reduction. This was an unanswered preference question, not a user-selected value.
- API setup is still required. Trial Gemini's free tier with no billing upgrade or paid fallback, conditional on eligible account access and suitable intended use. Default model `gemini-3.8-flash`, as listed in the official pricing and structured-output documentation inspected on October 10. Keep the model configurable through `GEMINI_MODEL`.
- API access and an operational Docker runner are prerequisites to a live end-to-end demo. Docker has been updated and its daemon and a basic restricted container work; the full project runner and its integration tests remain unimplemented.
- Run all submitted and AI-generated executable code in restricted containers. Never silently substitute direct host execution.

## User workflow

1. Open the local application. A compact readiness indicator shows API configuration and runner availability without exposing credentials.
2. Paste the statement or upload a saved HTML page. Show editable extracted text and separate editable sample input/output pairs. Preserve raw LaTeX notation in the text preview; visual equation rendering is not required.
3. Paste or upload C++ into an editable code area. Both entry methods populate the same field.
4. Click **Find counterexample**. Show the current stage, elapsed time, valid tests completed, and Cancel. Use a stage list, not a fabricated completion percentage.
5. Display a result with copy buttons for the reduced input and observed outputs. Put seed, source hashes, reference code, validation evidence, and reference method in an expandable details panel.

Use a restrained developer-tool layout: two input panels, one primary action, and a results area. Stack panels on narrow screens. Use native accessible controls and monospace input/output fields. No dashboard, login, branding assets, or decorative animations.

## HTML and text ingestion

Use Beautiful Soup's HTML parser to select `.problem-statement`. Extract the title, body, input/output specifications, limits, samples, and notes using classes rather than translated headings. Exclude navigation and unrelated document content.

Preserve block boundaries, list items, superscripts/subscripts, and sample line breaks. Prefer original `$$$...$$$` math. If saved rendered math exposes TeX through math script nodes or annotations, extract that text once; never execute it. Treat image-only math or missing required statement sections as extraction warnings requiring correction before running. Do not render uploaded markup or fetch remote resources.

The supplied Russian page contains all required sections and original LaTeX. Its sample input has 17 meaningful lines; its output is `4`, `27`, `0`, `10`, on separate lines. Sample lines are nested `<div>` elements inside `<pre>`. A naïve text concatenation would corrupt them.

Accept HTML files up to 5 MiB, C++ files up to 256 KiB, and normalized statement text up to 100,000 characters. Decode UTF-8 or a declared supported encoding; report decoding errors rather than silently replacing mathematical symbols. Require a nonempty statement, C++ source, and at least one complete sample pair. For pasted text, provide sample fields explicitly instead of guessing their boundaries with AI.

## Architecture and execution boundary

Use Python 3.12+ with FastAPI, Uvicorn, Pydantic, Beautiful Soup, and the Google GenAI SDK. Serve buildless HTML/CSS/JavaScript from the same process; no React, frontend build pipeline, database, or job broker. Pin tested dependency versions during implementation. Use pytest and FastAPI's test client for backend tests and Playwright for the main browser journey.

Separate ingestion, AI adapter, runner, search/reduction, and HTTP/UI responsibilities. Store run artifacts beneath ignored `.runs/<uuid>/` directories; keep the job registry in memory. Server restart does not resume runs. Retain completed artifacts locally for inspection and document manual cleanup.

Use a custom ARM64-compatible runner image based on Python 3.12 slim Bookworm with GNU g++ installed. Compile with `g++ -std=gnu++17 -O2 -pipe`, supporting ordinary Codeforces headers such as `bits/stdc++.h`. The image is built once before a run, not inside its three-minute budget.

Create separate per-run container roles for the submitted solution, primary reference/harness, and corroborating reference. Keep role inputs separate so reference processes cannot inspect candidate code or the other reference. Use no network, a non-root user, a read-only root filesystem, dropped capabilities, no-new-privileges, the default seccomp profile, 128 PIDs, 1 CPU per container, and bounded tmpfs workspaces. Limit compilation to 1 GiB RAM and 20 seconds; runtime roles to 512 MiB. Never mount the home directory, repository, Docker socket, or API credentials into a runner. Only mount each role's necessary source files read-only.

The host starts trusted runner commands with argument arrays, not interpolated shell commands. Generated Python modules are imported only inside a runner. Each execution uses a fresh child process with a two-second timeout and 64 KiB stdout/stderr caps. Kill process groups on timeout. Cancellation and final cleanup force-remove all containers belonging to that run. Readiness fails if containment is unavailable.

## AI and search pipeline

1. **Prepare:** Compile the submitted solution. Request a structured primary bundle using only the statement and samples, never the submitted algorithm. The bundle contains a brute-force Python reference, problem-aware parser/serializer, input validator, generator, reducer, and a plain-language explanation of the exhaustive method and its small-input limits.
2. **Check the reference:** Validate the bundle structure, run all samples against the reference, and check parsing/serialization round trips and validator behavior on its generated cases. Permit one repair request for a malformed or failing bundle. If checks still fail or a sample exceeds the reference execution limit, stop as reference preparation failed; do not proceed with an unchecked oracle.
3. **Search:** Run samples first, then bounded exhaustive tiny cases, seeded random cases, and deterministic adversarial families. The model writes generators, not lists of supposedly random test cases. Generated cases must satisfy original constraints, including coupled dimensions, array lengths, and aggregate bounds. Deduplicate serialized inputs. Compare whitespace-separated signed integer output tokens using arbitrary-precision integers. Malformed or extra output tokens count as an output mismatch only after the reference succeeds.
4. **Corroborate:** On the first disagreement, ask for a separately generated reference and validator using the statement and samples only, without the primary code, candidate code, or their answers. Check samples again, then require both validators to accept the failing input and both references to produce the same answer. If they disagree, crash, time out, or cannot finish within the budget, present an unconfirmed disagreement, not a confirmed wrong answer.
5. **Reduce:** Use the primary problem-aware reducer to propose simpler structured inputs. Accept a proposal only when it has fewer integer tokens or the same token count with a smaller sum of absolute integer values; both validators accept it, both references agree, and the submitted solution still disagrees. Re-run from the accepted case until no improving candidate survives or the deadline is reached. Keep the smallest confirmed case seen; do not claim global minimality.
6. **Explain:** If time and request budget remain, request a short explanation using the final case, executed outputs, submitted code, and reference method. Label this explanation AI-generated. If unavailable, still show the actual comparison and reference method. Model prose never supplies or overrides expected output.

Start the shared 180-second deadline at run creation. Allow at most four model calls total: primary bundle, one repair shared across preparation stages, corroborating bundle, and explanation. Each call is bounded by 45 seconds and the remaining overall time. Do not automatically retry quota errors or switch to paid service. Stop searching for a first discrepancy after 120 seconds to leave room for confirmation; if none exists, return an inconclusive result. Stop after 10,000 generated candidates even if time remains. Use at most 256 exhaustive cases, then alternate seeded random and adversarial cases. Generated problem-specific bounds must keep cases within the intended brute-force domain; invalid cases and timeouts consume budget and are counted separately.

Check cancellation between operations and while awaiting subprocess/API completion. Any partially found case remains accessible if later reduction or explanation cannot finish. Target crashes/timeouts are shown separately as runtime findings, not mistaken for algorithmic output counterexamples.

## Minimal interfaces

- `POST /api/import`: multipart saved HTML; returns editable normalized statement, title, sample pairs, and extraction warnings.
- `GET /api/health`: API-key presence, configured model, and runner readiness; never returns secrets.
- `POST /api/runs`: JSON with statement, sample pairs, C++ source, and optional integer seed; returns a run ID. Reject a second active run with 409.
- `GET /api/runs/{id}`: stage, elapsed time, counts, and eventual result. Browser polls once per second.
- `POST /api/runs/{id}/cancel`: idempotently request cancellation.

Core types are `ProblemInput`, `SamplePair`, `GeneratedBundle`, `ExecutionResult`, `RunSnapshot`, and `CounterexampleResult`, all validated with Pydantic. Define contracts before subsystem implementation.

Generated modules expose `parse(stdin) -> JSON case`, `render(case) -> stdin`, `valid(case) -> bool`, `generate(seed, index, mode) -> case | null`, `shrink(case) -> bounded list of cases`, and `solve(stdin) -> stdout`. The corroborating module supplies `valid_input(stdin) -> bool` and `solve(stdin) -> stdout`. The trusted container worker transports requests/results as bounded JSON and captures generated stdout separately from protocol messages.

Bind the HTTP server to loopback, allow only local Host headers, and enforce same-origin requests on writes. API keys live only in server environment variables; never browser storage, logs, prompts, repository content, or containers. Treat statements, uploaded HTML, source comments, and model responses as untrusted data, not host instructions.

## Result semantics and acceptance

Final outcomes are corroborated counterexample, unconfirmed disagreement, no counterexample found within limits, runtime finding, preparation/provider/runner failure, or cancelled. A corroborated result means repeatable execution plus two separately generated references agreeing, not a mathematical proof. No successful search path may assert that the submitted algorithm is correct. Show exactly which checks passed.

Evaluate five fixed integer/array problems, each with an independently reviewed reference and at least one correct and one deliberately incorrect C++ solution. Include the uploaded three-cyclic-arrays problem after checking its ground truth by direct enumeration. Freeze fixtures before evaluation, record seeds and all failures, and do not present selected successes as the complete benchmark.

Acceptance requires: faithful import of the supplied page; reproducible runs; a known wrong solution producing a corroborated, valid failing case on at least three of five benchmark problems within 180 seconds; zero false corroborated findings on the five correct controls; preserved mismatch after reduction; explicit failures for unavailable dependencies/quota; and tested process cancellation and containment. Three-of-five is a minimum demo acceptance target, not a claimed result or guarantee of broader coverage.

## Delivery and evidence

Create a public repository under And850 during implementation, excluding secrets, raw saved webpages, and `.runs`. Commit implementation in small verified steps. Include a README with local setup, free API configuration, supported problem scope, measured benchmark results, and limitations. There is no hosted execution service.

Prepare a 2–3 minute video showing HTML/C++ input, a real search, the reduced failure, and a brief code walkthrough. If recorded artifacts are used to explain a stage, label them as recorded; do not present them as a live API run. Submission also needs the public source link, project description, and local setup instructions. Submit by October 11, 2026 at 20:59 Europe/Madrid; target readiness by 19:30.

References checked October 10, 2026:
- https://evohackathon2026.devpost.com/ — judging and submission requirements.
- https://ai.google.dev/gemini-api/docs/pricing — free-tier availability.
- https://ai.google.dev/gemini-api/docs/structured-output — structured responses.
- https://docs.docker.com/engine/containers/run/ — runner isolation options.
- https://docs.docker.com/engine/containers/resource_constraints/ — resource limits.
