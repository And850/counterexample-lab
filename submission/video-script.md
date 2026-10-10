# Two-minute demonstration script

This is an evidence walkthrough from a real local model run. The generated video contains silent slides; use this narration when recording or presenting. It is not a recording of an unverified browser session.

**0:00–0:20 — The problem**

“I have competed in programming for six years. When an algorithm is wrong but the samples pass, finding the counterexample can take longer than writing the solution. AI often suggests a patterned input without checking it. Counterexample Lab automates the search and executes the evidence.”

**0:20–0:40 — The input**

“Here is a deliberately wrong C++ solution: it prints the absolute value of the sum. The sample, two and three, still produces five. In the app I can paste the statement or import a saved Codeforces HTML page, review the samples, and paste or upload my C++ file.”

**0:40–1:00 — The automation**

“The local model generates a parser, validator, brute-force solver, generators, and reducer. Restricted Docker containers execute the submitted program and generated Python. The workflow checks all samples before searching tiny exhaustive, random and boundary cases.”

**1:00–1:20 — Executed evidence**

“This real run found input zero and negative one hundred. The expected answer is negative one hundred; the submitted program prints positive one hundred. A fresh independent reference sees only the statement and samples. Both references and both input validators agreed. The full run took about fifty-six seconds.”

**1:20–1:40 — Inspectability**

“The result contains executed input and output, both Python references, source hashes, seed and case counts. Reduction accepts only valid smaller inputs that still disagree after fresh executions. Evidence survives failed explanation or interrupted reduction.”

**1:40–2:00 — Honest limits**

“An unsuccessful search is inconclusive. AI references may share a mistake, and this is not a proof or a globally minimal testcase. The current scope is C++17 with unique integer output. The repository includes correct controls and every benchmark attempt. It runs locally with a free model and requires no paid API.”

Before submitting, review the benchmark report, narrate the video, and upload it to the submission platform. The strict deadline is October 11, 20:59 Europe/Madrid. No Devpost submission has been made automatically.
