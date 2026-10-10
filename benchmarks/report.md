# Live evaluation

40 recorded runs across 5 fixed problems. Seed: 850. See `models.json` for loaded model/configuration and `prompt-versions.json` for prompt text. Every failed preparation or service request is retained.

## Attempt round 1

10/10 runs recorded. 1/5 wrong controls produced independently reviewed, valid corroborated evidence within 180 seconds.

| Problem | Candidate | Outcome | Seconds | Tested | Ground truth checked |
|---|---|---|---:|---:|---|
| sum | wrong | corroborated_counterexample | 85.33 | 2 | agrees |
| sum | correct | inconclusive | 120.05 | 114 | not checked |
| nonempty-interval | wrong | preparation_failure | 69.76 | 0 | not checked |
| nonempty-interval | correct | preparation_failure | 64.11 | 0 | not checked |
| knapsack | wrong | inconclusive | 120.53 | 89 | not checked |
| knapsack | correct | preparation_failure | 89.60 | 0 | not checked |
| distinct | wrong | preparation_failure | 64.02 | 0 | not checked |
| distinct | correct | preparation_failure | 57.53 | 0 | not checked |
| cyclic-snowmen | wrong | provider_failure | 42.95 | 0 | not checked |
| cyclic-snowmen | correct | provider_failure | 40.51 | 0 | not checked |

## Attempt round 2

10/10 runs recorded. 1/5 wrong controls produced independently reviewed, valid corroborated evidence within 180 seconds.

| Problem | Candidate | Outcome | Seconds | Tested | Ground truth checked |
|---|---|---|---:|---:|---|
| sum | wrong | preparation_failure | 43.70 | 0 | not checked |
| sum | correct | preparation_failure | 36.60 | 0 | not checked |
| nonempty-interval | wrong | preparation_failure | 48.64 | 0 | not checked |
| nonempty-interval | correct | preparation_failure | 54.99 | 0 | not checked |
| knapsack | wrong | provider_failure | 87.62 | 0 | not checked |
| knapsack | correct | preparation_failure | 81.20 | 0 | not checked |
| distinct | wrong | corroborated_counterexample | 112.33 | 26 | agrees |
| distinct | correct | preparation_failure | 47.13 | 0 | not checked |
| cyclic-snowmen | wrong | provider_failure | 85.89 | 0 | not checked |
| cyclic-snowmen | correct | provider_failure | 85.54 | 0 | not checked |

## Attempt round 3

10/10 runs recorded. 0/5 wrong controls produced independently reviewed, valid corroborated evidence within 180 seconds.

| Problem | Candidate | Outcome | Seconds | Tested | Ground truth checked |
|---|---|---|---:|---:|---|
| sum | wrong | preparation_failure | 14.37 | 0 | not checked |
| sum | correct | preparation_failure | 11.48 | 0 | not checked |
| nonempty-interval | wrong | preparation_failure | 11.12 | 0 | not checked |
| nonempty-interval | correct | preparation_failure | 12.44 | 0 | not checked |
| knapsack | wrong | preparation_failure | 16.27 | 0 | not checked |
| knapsack | correct | preparation_failure | 12.44 | 0 | not checked |
| distinct | wrong | preparation_failure | 9.70 | 0 | not checked |
| distinct | correct | preparation_failure | 9.25 | 0 | not checked |
| cyclic-snowmen | wrong | preparation_failure | 21.84 | 0 | not checked |
| cyclic-snowmen | correct | preparation_failure | 16.43 | 0 | not checked |

## Attempt round 4

4/10 runs recorded. 1/5 wrong controls produced independently reviewed, valid corroborated evidence within 180 seconds.

| Problem | Candidate | Outcome | Seconds | Tested | Ground truth checked |
|---|---|---|---:|---:|---|
| sum | wrong | corroborated_counterexample | 62.25 | 2 | agrees |
| sum | correct | preparation_failure | 36.78 | 0 | not checked |
| nonempty-interval | wrong | provider_failure | 85.81 | 0 | not checked |
| nonempty-interval | correct | evaluation_interrupted | >=40.30 | 0 | not checked |

Interrupted-attempt time is the last logged progress, a lower bound (>=), not a completed run duration.

## Attempt round 5

6/10 runs recorded. 0/5 wrong controls produced independently reviewed, valid corroborated evidence within 180 seconds.

| Problem | Candidate | Outcome | Seconds | Tested | Ground truth checked |
|---|---|---|---:|---:|---|
| sum | wrong | preparation_failure | 49.97 | 0 | not checked |
| sum | correct | inconclusive | 120.20 | 76 | not checked |
| nonempty-interval | wrong | preparation_failure | 69.32 | 0 | not checked |
| nonempty-interval | correct | preparation_failure | 59.05 | 0 | not checked |
| knapsack | wrong | preparation_failure | 78.66 | 0 | not checked |
| knapsack | correct | preparation_failure | 79.07 | 0 | not checked |

## Acceptance assessment

Observed coverage across the recorded rounds: **2/5** wrong-control problems. False corroborated findings on correct controls: **0**. Minimum target (3/5 in a complete ten-run round, and zero false findings): **not met**; this is not a guarantee of general performance.

Repeated rounds use fresh model generations and are reported separately. Coverage across rounds is not a first-attempt success rate. Preparation failures and inconclusive searches are not evidence of correctness. Several controls may fail preparation; the table makes that visible.

Independent benchmark validators check dimensions, value ranges and original aggregate limits. Independently authored definitions compare expected outputs with ground truth; cyclic-array enumeration is bounded to n<=10 and sum n<=100 so evaluation cannot run an unbounded host workload. The raw result messages in `results.json` retain failure reasons.
