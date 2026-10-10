# Recorded Gemini results

`attempt-7/` contains the complete result JSON for all ten controls in the Gemini 3.8 Flash round, including inconclusive, unconfirmed and provider-failure outcomes. These are recorded executions, not a live service response or a fixture mode in the app.

Problem statements and candidate C++ sources are frozen in [cases.json](../cases.json). Model configuration, prompts and the complete history are in [models.json](../models.json), [prompt-versions.json](../prompt-versions.json) and [results.json](../results.json). The [report](../report.md) assesses complete rounds separately from combined coverage.

Where evidence exists, its candidate/reference SHA-256 hashes were checked against the fixed candidate source and recorded reference text. Independent validators and exhaustive definitions checked the retained input and expected output. References remain untrusted source data and must run only in the restricted Docker roles; no generated code was imported on the host.

Three wrong controls were corroborated. Distinct counting remained unconfirmed. Three correct controls completed inconclusively; two provider failures provide no evidence of correctness. The last request hit a quota/rate limit. Billing was unchanged and no automatic retry or paid fallback occurred.
