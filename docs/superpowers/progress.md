# Implementation progress

Updated October 11, 2026. Delivery: [And850/counterexample-lab](https://github.com/And850/counterexample-lab). Core implementation began after kickoff. Changes are published through the GitHub API because local Git metadata is read-only.

## Task status

1. **Complete:** prerequisites, pinned runner image, restricted role containers, bounded execution and cleanup. Initial acceptance: 28 tests passed.
2. **Complete:** typed contracts and saved-HTML importer. The supplied personal Codeforces page retained all 17 input lines, four output lines, raw math and constraints. Only synthetic HTML fixtures are public. Full suite at acceptance: 41 passed.
3. **Complete:** Gemini and LM Studio adapters, bounded structured output, sample/round-trip/generator preparation, one shared repair, four-call limit and sanitized provider failures. Both providers have produced real end-to-end corroborated evidence.
4. **Complete:** seeded exhaustive/random/adversarial search, independent corroboration and valid reduction. Tests cover wrong references, correct controls, coupled dimensions, deadline/cancellation, preserved evidence and cleanup. Generated/submitted code executes only inside Docker.
5. **Implemented; browser verification gap:** local API, paste/upload interface, samples, readiness, progress, cancellation and downloadable JSON. API and offline DOM journeys pass. Real browser/visual verification remains outstanding because the browser tool denied localhost access. No alternate browser workaround was attempted.
6. **Package prepared; benchmark target met:** five fixed problems and ten controls per complete round; independent ground-truth validation; all failures retained. README, Devpost draft, narration and a silent 120-second evidence walkthrough are prepared. No Devpost submission has been made. Real-browser verification and submission upload remain external completion steps.

## Current verification

- **103 pytest tests passed**, 163.04 seconds. Docker-dependent checks were not skipped. One Google SDK deprecation warning concerns Python 3.17, not a failing test.
- Offline DOM journeys pass for paste/upload, sample editing, cancellation, safe evidence text and failure retention. These do not verify visual layout or a real browser.
- Fresh read-only release review found no remaining actionable code issue. It verified 28 API/provider/preparation tests, including physical source-line decoding followed by actual Docker preparation. Its setup-document correction was applied.
- Source responses use bounded arrays of physical Python lines, preserve indentation and blank lines, and are joined as text before the unchanged external contract is validated. Neither decoding nor preparation imports generated code on the host.
- The API elapsed timer advances from job creation during model waits; terminal elapsed remains fixed. Gemini SDK quota errors receive sanitized messages without retry or provider switching.
- The current application on [port 8002](http://127.0.0.1:8002) serves HTTP 200 for the interface and health route, with Docker ready and Gemini selected. Private credentials were preserved; billing was not activated or modified. Local LM Studio configuration remains available as a manual alternative.

## Live evidence and evaluation

A local smoke run corroborated `0 -100`, expected `-100`, actual `100`, in 55.9 seconds. The durable local benchmark evidence used by the walkthrough records the same failing input in **85.3 seconds**. A Gemini smoke corroborated `0 -1`, expected `-1`, actual `1`, in **28.7 seconds**; its complete evidence is public under `submission/evidence-gemini.json`.

Six local evaluation rounds retain 54 records, including one interrupted round. Combined local coverage is 3/5 wrong-control problems, but no complete local round met the 3/5 target. The sixth round corroborated knapsack in 116.69 seconds and otherwise had preparation/provider failures. Correct-control preparation failures are not evidence of correctness.

Gemini round 7 completed all ten controls in a separate output directory; the records were merged only after both processes finished. It corroborated **3/5** wrong controls: sum (49.25 seconds), nonempty maximum interval (35.34 seconds), and knapsack (59.41 seconds). Three correct controls completed inconclusively, while distinct and cyclic-array correct controls failed at the provider stage. Distinct counting remained unconfirmed; cyclic-array wrong generation was truncated and the final correct-control request hit a quota/rate limit. These failures remain visible and are not evidence of correctness. No retry or paid fallback was attempted after quota failure.

The minimum complete-round benchmark target is met, with **zero false corroborated correct-control findings**. All **64 runs** remain in the report; combined wrong-control coverage is 4/5 across rounds, not a first-attempt success rate. Full JSON for all ten Gemini controls is published under `benchmarks/evidence/attempt-7/`. Retained inputs, independent ground truth and candidate/reference hashes were rechecked from those serialized records. No role containers remained after the round. The [benchmark report](../../benchmarks/report.md) distinguishes complete rounds, aggregate coverage and false correct-control findings.

Benchmark ground-truth definitions validate original dimensions, ranges and aggregate constraints before bounded host enumeration. An interrupted attempt retains its last logged elapsed time as a lower bound and cannot qualify a round. No failed preparation or service request is discarded.

## Fresh setup and delivery

The published archive at `3d4944317ca21c62ccef6993e419ade6a22f48eb` was checked in a separate environment: pinned dependency installation, runner image build, server import, C++ compilation/execution yielding `42` only inside Docker, and successful cleanup. The later `e39e678493ca55d397a65d3cae710755f1411afa` archive also passed source-line decoding and container compilation. Both were checked to contain no `.env`.

Final release `9a7691d3d83dd82607790fd450a60d1c120cb56c` published 73 verified files. Its downloaded archive contains no `.env`, includes all ten Gemini results and retains the same pinned requirements. Using the separate installed environment, its interface/health routes, physical source-line contract, Docker-only C++ execution yielding `42`, and cleanup passed. A final container audit was empty; the current app still serves HTTP 200 on port 8002. No generation retry was made after the observed quota failure.

The walkthrough renders from public `submission/evidence-example.json`; its duration is 120 seconds and the evidence slide was visually inspected. It is labeled recorded evidence, not a browser screen recording. The video is local and excluded from Git; its renderer and narration are public.

Heartbeat scheduling was rejected by the app's automatic approval policy (`never`), so no recurring automation was created. Work continued in the active session. A prior development server could not be terminated under the sandbox policy; it was left intact and the app uses a separate free port. Later servers created by this session were restarted through their owned terminal sessions.
