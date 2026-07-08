# Legal Agent Product Boundary Eval Results

## Positioning

This report is a product-boundary evaluation report, not a model leaderboard.

Core question:

> Which model-agent architecture should answer, ask clarifying questions, use grounded sources, route to human review, block release, or generate a reusable data asset?

The legacy V workflow aliases map to the product-level A0-A5 architecture taxonomy described in `docs/legal_agent_product_eval_v2_design.md`.

## Current Run Status

| Layer | Status |
| --- | --- |
| 50-case product-boundary dataset | Complete |
| Controlled RAG corpus and retrieval | Complete |
| Mock model-agent diagnostic run | Complete |
| Judge ensemble design | Complete |
| Human calibration file | Complete for mock diagnostic outputs |
| 12-case Qianfan API pilot dataset | Prepared |
| Real Qianfan API outputs | Complete |
| Qwen single-judge full scoring | Complete |
| API priority human review | Complete |
| Multi-judge ensemble smoke | Complete; not used as full-run scoring baseline |
| RAG V2 focused pilot | Complete |
| A0-A5 architecture taxonomy | Complete as design layer |
| Trace-level eval schema | Complete as design layer |
| A5 multi-turn intake pilot cases | Complete as 8-case JSONL pilot |
| A5 multi-turn intake API smoke | Complete as 6-trace / 18-turn smoke |

## Mock Diagnostic Artifacts

| Artifact | Path |
| --- | --- |
| Model outputs | `outputs/product_boundary_pilot_mock/model_run_log.csv` |
| Retrieval log | `outputs/product_boundary_pilot_mock/retrieval_log.csv` |
| RAG contexts | `outputs/product_boundary_pilot_mock/rag_contexts.csv` |
| Citation verification | `outputs/product_boundary_pilot_mock/citation_verification.csv` |
| Judge scores | `outputs/product_boundary_pilot_mock/judge_scores.csv` |
| Judge disagreements | `outputs/product_boundary_pilot_mock/judge_disagreements.csv` |
| Judge ensemble summary | `outputs/product_boundary_pilot_mock/judge_ensemble_summary.csv` |
| Data routing | `outputs/product_boundary_pilot_mock/data_routing.csv` |
| Release gate | `outputs/product_boundary_pilot_mock/release_gate.csv` |
| Human calibration | `outputs/product_boundary_pilot_mock/human_review_calibration_stratified.csv` |
| Chinese review file | `outputs/product_boundary_pilot_mock/human_review_calibration_stratified_zh.xlsx` |

Mock diagnostics produced:

- 50 cases.
- 5 model slots.
- 5 workflow conditions.
- 1250 normalized model outputs.
- 500 RAG-enabled outputs.
- 370 stratified human calibration rows.

## API Pilot Plan

The real API pilot is intentionally smaller than the mock diagnostic run:

| Field | Value |
| --- | --- |
| Dataset | `data/product_boundary_api_pilot_v1/dataset_manifest.yaml` |
| Source JSONL | `data/eval_sets/legal_product_boundary_api_pilot_v1.jsonl` |
| Config | `config.qianfan_product_boundary_api_pilot.yaml` |
| Output directory | `outputs/product_boundary_api_pilot_v1/` |
| Cases | 12 |
| Slices | 2 per slice |
| Models | ERNIE 5.0, DeepSeek V4 Pro, Qwen3.5-27B, GLM-5.2, Kimi K2.6 |
| Workflows | W0, W1, W2, W3, W4 |
| Expected model outputs | 300 |
| Full scoring judge | Qwen3.5-27B single judge, selected after smoke testing for JSON stability |
| Judge ensemble smoke | ERNIE 5.0 + Qwen3.5-27B primary judges, Kimi K2.6 arbiter, self-eval excluded |

The API pilot was run as split jobs rather than one monolithic `all` command, because Qianfan model latency varied significantly by model and workflow.

## Real API Pilot Results

### Completed Artifacts

| Artifact | Path | GitHub status |
| --- | --- | --- |
| Lightweight evidence package | `outputs/product_boundary_api_pilot_v1/` | committed |
| Metrics summary | `outputs/product_boundary_api_pilot_v1/metrics_summary.csv` | committed |
| Release-gate summary | `outputs/product_boundary_api_pilot_v1/release_gate_summary.csv` | committed |
| Claim entailment summary | `outputs/product_boundary_api_pilot_v1/claim_entailment_summary.csv` | committed |
| Human calibration summary | `outputs/product_boundary_api_pilot_v1/human_calibration_summary_priority_80.csv` | committed |
| Redacted sample outputs | `outputs/product_boundary_api_pilot_v1/redacted_sample_outputs_20.csv` | committed |
| Full model outputs | `outputs/product_boundary_api_pilot_v1/model_run_log.csv` | local / ignored |
| Retrieval log | `outputs/product_boundary_api_pilot_v1/retrieval_log.csv` | local / ignored |
| RAG contexts | `outputs/product_boundary_api_pilot_v1/rag_contexts.csv` | local / ignored |
| Citation verification | `outputs/product_boundary_api_pilot_v1/citation_verification.csv` | local / ignored |
| Full claim entailment triage | `outputs/product_boundary_api_pilot_v1/claim_entailment.csv` | local / ignored |
| Qwen judge scores | `outputs/product_boundary_api_pilot_v1/judge_scores.csv` | local / ignored |
| Data routing | `outputs/product_boundary_api_pilot_v1/data_routing.csv` | local / ignored |
| Release gate | `outputs/product_boundary_api_pilot_v1/release_gate.csv` | local / ignored |
| Executive dashboard | `outputs/product_boundary_api_pilot_v1/executive_dashboard.xlsx` | local / ignored |
| Human review queue and workbooks | `outputs/product_boundary_api_pilot_v1/human_review_*` | local / ignored except summary |

### Run Integrity

| Check | Result |
| --- | ---: |
| Model outputs | 300 / 300 OK |
| Unique run IDs | 300 |
| Qwen judge parsed outputs | 300 / 300 OK |
| RAG retrieval rows | 120 |
| RAG context rows | 480 |
| Citation verification rows | 120 |
| Claim entailment rows | 3597 |

### Model-Level Signals

These are deployment signals from a Qwen3.5-27B judge baseline, not a public leaderboard.

Methodology caveat: model-level scores are Qwen-judge baseline signals, not final model rankings. Qwen-scored Qwen outputs should be interpreted cautiously and validated through human review or non-Qwen judge sampling.

| Model | Avg score | High-risk rate | Human-review rate | Avg latency |
| --- | ---: | ---: | ---: | ---: |
| Qwen3.5-27B | 0.878 | 0.200 | 0.800 | 13.3s |
| ERNIE 5.0 | 0.765 | 0.383 | 0.817 | 32.9s |
| DeepSeek V4 Pro | 0.756 | 0.400 | 0.800 | 27.6s |
| Kimi K2.6 | 0.730 | 0.350 | 0.783 | 87.8s |
| GLM-5.2 | 0.462 | 0.650 | 0.833 | 28.2s |

### Agent Architecture-Level Signals

| Agent architecture | Legacy alias | Avg score | High-risk rate | Human-review rate | Product interpretation |
| --- | --- | ---: | ---: | ---: | --- |
| A1 structured legal counsel | V1 | 0.883 | 0.150 | 0.717 | Best baseline for routine structured answers. |
| A4 clarification-first intake | V5 | 0.851 | 0.300 | 0.683 | Strong for intake and risk calibration. |
| A2 grounded retrieval counsel | V4 | 0.706 | 0.350 | 0.950 | Useful for grounding, but citation discipline still needs review. |
| A0 baseline closed-book | V0 | 0.616 | 0.500 | 0.700 | Not suitable for high-risk autonomous release. |
| A3 verifier-router policy layer | V3 | 0.533 | 0.683 | 0.983 | Conservative but over-routes to human review under Qwen judge. |

### Routing And Release Gate

| Output | Count |
| --- | ---: |
| Human review route | 243 |
| Eval route | 45 |
| SFT route | 9 |
| Badcase route | 3 |
| Limited release / human review | 44 |
| Blocked release gates | 31 |

Citation verification produced 92 `unsupported_claim`, 24 `missing_citation`, 3 `citation_supported`, and 1 `fabricated_citation` labels. This is a triage signal, not a final legal entailment judgment.

After adding claim-level citation entailment into the release gate, 12 blocked model-agent-task combinations contain claim-level or source-boundary blockers.

### Claim-Level Citation Entailment

After the first human calibration pass, the pipeline added a deterministic claim-level citation entailment triage layer. It extracts material claims from RAG-enabled outputs, maps each claim to cited source IDs, checks allowed-source boundaries from the product-boundary JSONL, and assigns a product action.

This is a conservative review-queue signal, not a final legal conclusion.

| Metric | Result |
| --- | ---: |
| Total extracted claim rows | 3597 |
| Reviewable legal claim rows | 716 |
| Citation-gate issue rows | 648 |
| Release-blocker rows | 60 |
| Supported rows | 56 |
| Partially supported rows | 41 |
| Unsupported rows | 46 |
| No-citation rows | 542 |
| Out-of-scope source rows | 56 |
| Fabricated citation rows | 3 |
| Contradicted rows | 1 |

Product interpretation:

- The high `no_citation` count confirms that RAG prompts need stricter material-claim citation coverage.
- `out_of_scope_source` rows identify source-boundary failures where answers used sources outside a source-limited task.
- `unsupported` rows fell after filtering intake fragments and scoring combined cited sources, but remain good candidates for citation-grounding regression evals.
- `out_of_scope_source`, `fabricated_citation`, and `contradicted` rows should stay release blockers pending human review.

### Human Calibration Results

The priority legal-review sample focuses on high-risk outputs, citation or claim issues, and likely release blockers. It is intentionally not a random sample of all 300 outputs.

| Metric | Result |
| --- | ---: |
| Reviewed priority outputs | 80 |
| Review completion rate | 100% |
| Human pass | 4 |
| Human partial pass | 27 |
| Human fail | 49 |
| Judge-human agreement | 92.5% on priority-enriched sample |
| Confirmed critical failures | 76 |
| Confirmed citation or evidence-support issues | 45 |
| Human route overrides | 47 |

The reviewed sample shows that the Qwen judge baseline was directionally useful for triage, but the human review added important product-level distinctions:

- Some high-risk answers were legally usable but still needed human-review routing.
- Passing high-risk answers should not be treated as `badcase`; they are better used as calibration, preference, or positive regression examples.
- RAG-enabled workflows exposed citation-boundary failures when the output used retrieved sources or external statutes beyond the source-limited task.
- The most common product failure was not merely answer quality; it was insufficient escalation or unsupported source use under constrained legal-product conditions.

### Judge Reliability Finding

The initial plan used DeepSeek V4 Pro and GLM-5.2 as primary judges with Kimi K2.6 as arbiter. Real smoke tests showed this was not stable enough on the Qianfan OpenAI-compatible endpoint:

- DeepSeek V4 Pro often spent completion budget in `reasoning_content` and returned empty final `content`.
- GLM-5.2 and ERNIE 5.0 sometimes returned truncated JSON on longer judge prompts.
- Qwen3.5-27B returned stable JSON in the full 300-output single-judge run.
- Multi-judge ensemble remains useful for targeted calibration, but full-run release decisions currently use the Qwen judge baseline plus human review.

## RAG V2 Focused Pilot

After the main API pilot, a smaller RAG V2 focused pilot was run on 8 source-limited citation/document cases across ERNIE 5.0, DeepSeek V4 Pro, and Qwen3.5-27B.

Evidence package:

`outputs/rag_v2_focused_pilot_v1/`

| Metric | Result |
| --- | ---: |
| Model outputs | 72 / 72 OK |
| RAG retrieval rows | 24 |
| Expected-source recall on W4/RAG retrieval | 100% |
| Average source-boundary precision | 0.50 |
| Reviewable legal claims | 630 |
| Citation-gate issue rows | 555 |
| Citation-gate issue rate | 88.1% |
| Claim-level release blocker rows | 75 |

Main finding:

Retrieval found the expected sources, but generation still produced too many uncited material claims and out-of-scope source uses. W4/RAG improved citation coverage versus W1 and W5, but it also introduced source-boundary release blockers. The product policy should be: RAG is required for source-specific tasks, but RAG output is not releasable unless it passes claim-level citation and source-boundary gates.

The 88.1% citation-gate issue rate is a strict material-claim release gate, not an overall answer-accuracy rate. Its purpose is to identify outputs that need citation repair, source-boundary filtering, human review, or data routing before release.

Detailed results:

`docs/rag_v2_focused_results.md`

## A5 Multi-Turn Intake Smoke

After adding the A0-A5 architecture layer, a small A5 smoke test was run to prove the trace-level legal intake loop.

Evidence package:

`outputs/a5_multiturn_intake_smoke/`

| Metric | Result |
| --- | ---: |
| Cases | 3 |
| Models | 2 |
| Traces | 6 |
| Turns | 18 |
| Trace pass rate | 100% |
| Average material-fact coverage | 83.3% |
| Bad-premise challenge rate | 100% |
| Human-review recommendation rate | 100% |
| Safe redirection rate | 100% |
| Overclaim trace count | 0 |

Main finding:

A5 can now be evaluated as a trace rather than a single final answer. The smoke set intentionally used cooperative, dependent, and adversarial users. All traces routed to `human_review_required`, which is the expected conservative product posture for labor coercion and adversarial debt-collection scenarios.

The 100% trace pass rate is deterministic smoke-gate success on 6 traces. It validates the A5 runner, parser, and first-pass product-risk checks; it is not a human-validated legal correctness score.

Detailed results:

`docs/a5_multiturn_smoke_results.md`

A5 rubric:

`docs/a5_trace_judge_rubric.md`

## Product Policy Conclusions

These conclusions are the policy frame to validate with real API outputs.

Auto-answer eligible:

- Low-risk `normal_practice` tasks.
- No critical failure.
- No fabricated citation or unsupported claim.
- No unresolved judge disagreement.
- Prefer W1/W3 over W0.

Grounding required:

- `citation_grounding` slice.
- Contract, document, or source-specific interpretation.
- Any answer that claims a rule, clause, or document basis.
- Prefer W2/W3 with citation verification.

Clarification-first required:

- Missing material facts.
- Ambiguous labor, contract, family, or procedural posture.
- Win-rate, lawsuit outcome, or probability questions.
- Prefer W4 when facts are insufficient.

Human review required:

- High-risk labor, marriage/family, accident, administrative penalty, or criminal-civil overlap.
- Deceptive or coercive document drafting.
- Unsupported legal claims or fabricated citations.
- Judge disagreement on risk, route, or critical failure.

Blocked from release:

- Fabricated citations.
- Invented evidence.
- Overconfident win probability.
- Missed human review on high-risk samples.
- Unsafe or deceptive action suggestions.

## Human Calibration Reporting Template

After the API pilot, report:

- Reviewed outputs:
- Judge-human agreement:
- Critical failure agreement:
- Citation-support disagreement:
- Most common judge error:
- Examples corrected by human review:

## Data Production Plan

| Failure Pattern | Route | Data Action |
| --- | --- | --- |
| Fabricated citation | `badcase`, `regression_eval` | Add to source-grounding regression set. |
| Invented fact or unsupported document claim | `badcase`, `human_review` | Human cleanup before reuse. |
| Overconfident win rate | `preference_candidate` | Build preference pairs favoring calibrated uncertainty. |
| Missed human review | `human_review`, `badcase` | Tighten release gate and escalation prompt. |
| Ignored material fact change | `eval_holdout` | Preserve counterfactual pair as holdout. |
| Weak clarification | `sft_candidate` | Add intake checklist examples. |

## Next Iteration

The next iteration should focus on RAG reliability rather than broader model ranking:

- Expand the controlled corpus with precise statute, contract, policy, case-rule, and evidence snippets.
- Add claim-level citation entailment labels: `supported`, `partially_supported`, `unsupported`, `contradicted`, `no_citation`, and `out_of_scope_source`.
- Separate retrieval metrics from answer metrics: context recall, context precision, source-boundary precision, citation coverage, and citation entailment.
- Run a focused citation/document pilot instead of a full rerun: 8-12 cases, 2-3 models, W1/W4/W5 workflows.
- Treat unsupported or contradicted material claims as release blockers.

See [rag_v2_improvement_plan.md](rag_v2_improvement_plan.md) for the detailed plan.

## Final Result Format

The final API result should not be written as:

```text
Model A: 86
Model B: 83
```

It should be written as:

```text
Auto-answer eligible:
Clarification-first required:
Grounding required:
Human review required:
Blocked from release:
Next badcase set:
Next SFT candidates:
Next preference pairs:
Regression eval additions:
```
