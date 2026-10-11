# Narrated evidence walkthrough

Recorded evidence and actual source, with synthesized macOS narration. This is not a browser recording.

## Slide 1: Find the input that breaks it

After six years of competitive programming, finding a counterexample can still take longer than writing a solution. AI often suggests inputs without testing them. Counterexample Lab automates the search and executes the evidence. This is a recorded evidence and source walkthrough, with synthesized narration.

## Slide 2: Inputs and the hidden bug

This deliberately wrong C plus plus program prints the absolute value of the sum. Two and three still produce five, so the sample passes. The interface accepts pasted statements or saved Codeforces HTML, with editable samples. Paste your C plus plus seventeen solution or upload its source file.

## Slide 3: The automated testing workflow

The model generates an independent testing module: parser, renderer, validator, brute force solver, generators and reducer. Preparation checks all samples and input round trips. Restricted Docker containers execute every submission and reference. The search tries tiny exhaustive, random and adversarial inputs. A fresh independent request checks an observed disagreement.

## Slide 4: Today's executed Gemini result

Today's real Gemini run retained zero and negative one. The reference answer is negative one, while the submitted program prints positive one. Both sample checked references and both input validators agreed. The run finished in 69 seconds. The repository preserves its input, outputs, reference implementations, source hashes and counts.

## Slide 5: Inside the corroboration gate

Here is the actual corroboration gate in the search engine. Both validators and both reference outputs must agree. If either check fails, this branch returns an unconfirmed disagreement. Reduction then accepts only smaller valid inputs that still fail after fresh executions. No generated or submitted code is executed on the host.

## Slide 6: Measured coverage and honest limits

The complete Gemini benchmark corroborated three of five wrong controls, with zero false corroborated correct control findings. Three correct controls were inconclusive; two had provider failures. All sixty four attempts remain visible. This is evidence, not proof or a globally minimal case. The public repository provides local setup instructions. The current scope is C plus plus seventeen with unique integer outputs.
