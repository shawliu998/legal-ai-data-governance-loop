# Methodology Risk Register

This file turns known evaluation limitations into explicit product and data-governance actions.

| Risk                               | Current Status                                                                             | Mitigation Already Added                                                                                                                                    | Remaining Work                                                                                                                |
| ---------------------------------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| A5 was only a smoke test           | Upgraded from 6 traces to a 24-trace real API pilot across 8 cases and 3 models.           | Added `config.qianfan_a5_multiturn_pilot.yaml`, `outputs/a5_multiturn_intake_pilot_v1/`, A5 rubric, redacted trace example, and human calibration template. | Human-review all 24 traces before claiming A5 readiness.                                                                      |
| RAG corpus is controlled and small | Still a controlled corpus, not a full legal knowledge base.                                | RAG V2 explicitly frames results as source-limited reliability testing, not legal coverage.                                                                 | Expand to authoritative statute, case, contract, and policy sources; add hard negatives and retrieval-source boundary labels. |
| Claim entailment is triage         | Claim checks are deterministic release-risk signals, not final legal entailment judgments. | Results now describe the 88.1% citation-gate issue rate as a strict material-claim release gate, not model accuracy.                                        | Add human labels for support/contradiction, evidence-span matching, and sampled LLM entailment review.                        |
| Judge bias and self-judge risk     | Full 300-output scoring uses Qwen3.5-27B as a stable structured judge baseline.            | Added caveats, priority human review, and an ensemble-smoke design with self-eval exclusion.                                                                | Run non-Qwen judge sampling on a stratified subset and report judge-human agreement by slice.                                 |
| API sample size is pilot-scale     | Real API evidence is 300 product-boundary outputs, 72 RAG V2 outputs, and 72 A5 turns.     | README and results avoid statistical superiority claims and frame outputs as product-decision evidence.                                                     | Treat conclusions as deployment-policy hypotheses until larger stratified evaluation is run.                                  |

## Release Interpretation

The project should not claim:

- full legal correctness,
- production-ready autonomous legal advice,
- statistically significant model superiority,
- release-safe RAG,
- final judge accuracy.

The project can claim:

- real API outputs were collected,
- model-agent-workflow behavior was converted into release gates,
- RAG failures were decomposed into retrieval, citation, claim, and source-boundary issues,
- A5 multi-turn intake is now evaluated at trace level,
- failures are routed into human review, badcase, SFT, preference, and regression-eval data assets.
