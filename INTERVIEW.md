# Interview case study

Verified upgrade: 2026-11-05. Scope: job-switch and interview readiness.

Data Engineer and applied AI: corpus integrity and explainable ranking configuration.

## Architecture and engineering decision

Ingestion normalizes and validates tabular job records, derives searchable text and deduplicates jobs. The composite scorer combines lexical, skill, title, experience, parseability and optional semantic components.

JSONL is parsed record by record with line-specific errors. Schema defaults survive ingestion; empty/all-invalid inputs fail clearly. Structured deduplication keys preserve field and company boundaries. Caller weights are now honored, validated and copied rather than silently replaced.

## Five-minute walkthrough

Run synthetic JSONL ingestion, show distinct jobs remain distinct, then run a skill-only scoring configuration with the semantic model both available and unavailable. The score must follow the requested weights.

After the repository's documented dependency setup, run these commands from its root. Use an activated Python environment where applicable; Maven offline mode requires cached dependencies.

```text
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

## Recorded evidence

8 offline regression tests passed. Scoring tests stub only semantic model availability/output; lexical and composite code run locally. Full OCR, Oracle and provider integrations were not exercised.

On 2026-11-06, 11 tests passed after adding an HTTP regression for frontend path containment. The actual SPA route rejects encoded parent paths and Windows backslash traversal, while public assets and client routes remain available. The route is tested in an isolated FastAPI app so optional ML and Oracle services do not start.

Behavioral regressions were reproduced before their fixes. Passing contract tests demonstrate the named behavior; they are not an AI accuracy rating.

## Defensible resume wording

> Implemented validated job ingestion and configurable composite matching with regression checks for JSONL, corpus identity and semantic-model availability.

Use this wording only after you can reproduce and explain the implementation. Add measured numbers with their dataset and environment; never substitute synthetic results for real-user impact.

## Questions to prepare

Is a match score a calibrated hiring probability? How would you label relevant jobs and evaluate nDCG? What happens when an explicitly weighted model is unavailable?

## Remaining evidence

Ranking quality needs independently labeled resume/job pairs, baselines and slice analysis. Default semantic/nonsemantic policies remain heuristics; do not claim ATS-vendor equivalence or hiring outcomes.
