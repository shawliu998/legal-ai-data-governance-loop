# Methodology Risk Register

This file turns known evaluation limitations into explicit product and data-governance actions.

## Risk Register

### A5 Quality Signals Are Not Human-Calibrated

Current status:

- Upgraded from 6 traces to a 24-trace / 72-turn API pilot across 8 cases and 3 Qianfan-hosted model
  slots.
- Fixed lexical matching and negation-scope false positives; the current offline rerun has 0 lexical
  flags, which still does not establish 0 human-confirmed overclaims.

Mitigation already added:

- Added `configs/pilots/qianfan_a5_multiturn_pilot.yaml`, `outputs/a5_multiturn_intake_pilot_v1/`, A5
  rubric, redacted trace example, and human calibration template.

Remaining work:

- Human-review all 24 traces before reporting A5 quality metrics or claiming readiness.

### RAG Corpus Is Controlled And Small

Current status:

- Still a controlled corpus, not a full legal knowledge base.

Mitigation already added:

- RAG V2 explicitly frames results as source-limited reliability testing, not legal coverage.

Remaining work:

- Expand to authoritative statute, case, contract, and policy sources.
- Add hard negatives and retrieval-source boundary labels.

### Claim Entailment Is Triage

Current status:

- Claim checks are deterministic release-risk signals, not final legal entailment judgments.

Mitigation already added:

- Results separate 555/630 strict citation-defect flags, 591/630 claim-support needs-review flags
  (including 36 `partially_supported`), and 75/1766 all-claim source-boundary blockers; none is
  described as model accuracy.

Remaining work:

- Add human labels for support/contradiction, evidence-span matching, and sampled LLM entailment
  review.

### Judge Bias And Self-Judge Risk

Current status:

- The 300-run pilot uses the Qwen3.5-27B hosted slot as a structured judge baseline. Parseability is
  not judge accuracy, and 29 model responses are empty.

Mitigation already added:

- Added caveats, priority human review, and an ensemble-smoke design with self-eval exclusion.

Remaining work:

- Preserve reviewer A/B and adjudicated labels, then run non-Qwen judge sampling on random and
  priority strata before reporting reproducible evaluator metrics.

### API Sample Size Is Pilot-Scale

Current status:

- API evidence is 300 product-boundary run records (271 non-empty, 29 empty), 72 RAG V2 run records,
  and 24 A5 traces / 72 turns.

Mitigation already added:

- README and results avoid statistical superiority claims and frame outputs as product-decision
  evidence.

Remaining work:

- Treat conclusions as deployment-policy hypotheses until larger stratified evaluation is run.

## Release Interpretation

The project should not claim:

- full legal correctness,
- production-ready autonomous legal advice,
- statistically significant model superiority,
- release-safe RAG,
- final judge accuracy.

The project can claim:

- pilot-scale API run records were collected with empty responses preserved,
- model-agent-workflow behavior was converted into release gates,
- RAG failures were decomposed into retrieval, citation, claim, and source-boundary issues,
- A5 multi-turn intake is now evaluated at trace level,
- failures enter release/review workflows and, after review, may become badcase, eval, SFT,
  preference, or regression data-asset candidates.
