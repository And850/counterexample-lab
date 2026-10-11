# Counterexample Lab

**Tagline:** Find the input that breaks your C++ algorithm.

## Inspiration

After six years of competitive programming, I still spend too much time searching for counterexamples. When debugging and boundary checks do not reveal an incorrect algorithm, random testing becomes a needle-in-a-haystack exercise. AI suggestions often repeat patterned examples without actually executing them.

## What it does

Counterexample Lab automates the testing workflow. In a local browser, import a saved Codeforces HTML page or paste a statement and samples, then paste or upload a C++17 solution. AI creates an independent small-case solver, input validator, generator, and reducer. Docker executes the submission and references, compares integer outputs, and searches for a disagreement.

A fresh independent model request receives only the statement and samples. A mismatch is labeled corroborated only when both sample-checked references and both input validators agree. Valid smaller proposals are tested again against all three programs. Results include the input, expected and actual output, reference code, hashes, counts, seed, and a downloadable evidence file.

## How I built it

Python, FastAPI, Pydantic, Beautiful Soup, a buildless HTML/CSS/JavaScript interface, GNU C++17, and restricted Docker execution. Gemini 3.8 Flash serves structured model responses on the project's Free tier. LM Studio with local Qwen3.5-9B is an alternative requiring no API account. Both providers have produced real corroborated evidence; the repository reports their failures as well as their successes.

All generated and submitted code executes in separate restricted role containers. The host handles orchestration and structured data. Runs have a shared deadline, limited model calls, one repair allowance, cancellation, and bounded output.

## Challenges

Preserving Codeforces math and sample formatting from saved HTML; preventing an AI oracle mistake from masquerading as a confirmed bug; maintaining valid coupled dimensions during reduction; handling local model truncation and malformed modules; and cleaning up subprocess trees even when an execution hangs.

Native LM Studio generation with reasoning disabled worked better than the schema compatibility endpoint on the installed model. The app validates generated JSON and checks executable modules against all supplied samples before searching. It reports failures rather than substituting fabricated examples.

## Accomplishments

A live Gemini run found and corroborated an absolute-sum bug: input `0 -1`, expected `-1`, actual `1`, in 28.7 seconds. A fresh October 11 run reproduced the retained input and outputs in 69.1 seconds; its preserved evidence supplies the final narrated walkthrough, alongside an actual source-code excerpt. A local-model benchmark also found `0 -100`, expected `-100`, actual `100`, in 85.3 seconds. Deterministic regression tests exercise wrong references, correct controls, invalid proposals, coupled arrays, cancellation and container containment. All five fixed benchmark problems and both controls per problem are reported in the repository, including unsuccessful attempts.

The complete Gemini round corroborated 3/5 wrong controls with zero false corroborated correct-control findings. Three correct controls completed inconclusively; two failed at the provider stage. The repository retains 64 runs across seven rounds and full results for all ten Gemini controls. All 103 regression tests and offline interface journeys pass.

## Limitations and next steps

No disagreement within the budget is inconclusive. Two AI references can share a mistake; corroboration is not proof. Small-input testing can miss large-input bugs, and reduction does not establish global minimality. This version supports unique integer-token outputs in C++17; Java, PDF and custom output checkers remain future work.

The distinct-counting Gemini result stayed unconfirmed because its second reference did not finish. Cyclic-array generation failed on truncation and quota limits. Free API quotas constrain repeated runs; the app reports these failures and does not activate billing or change provider automatically.

Real browser/visual verification was blocked by this development session's browser permission policy. Offline DOM interaction checks and API tests are available; this limitation is disclosed rather than hidden.

The final video is a recorded evidence-and-source walkthrough with clearly labeled synthesized narration. It is not an interface screen recording.

## Access

Source and setup: https://github.com/And850/counterexample-lab

Run locally with Docker and either Gemini or LM Studio, then open the loopback browser interface. A public execution service is outside this project. See the README for exact commands and evaluation results.
