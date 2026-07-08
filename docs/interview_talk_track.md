# Interview Talk Track

## 30-Second Version

I built a legal AI product-boundary evaluation and data governance system. Instead of ranking models by average score, it evaluates whether a legal AI product should answer, ask clarifying questions, use grounded sources, route to human review, or block release. I ran a real Qianfan API pilot across ERNIE 5.0, DeepSeek V4 Pro, Qwen3.5-27B, GLM-5.2, and Kimi K2.6, then human-reviewed 80 priority outputs and added RAG V2 plus a 24-trace A5 multi-turn intake pilot. The output is not just scores; it is model-agent routing policy, trace-level risk signals, release gates, and next-round data production actions.

## 2-Minute Version

The project started from a practical product question: in legal AI, average model score is not enough. A model can sound fluent and still fabricate a citation, overstate litigation chances, miss a need for human review, or use sources outside the allowed materials.

So I designed the eval around product decisions:

- Can the model answer?
- Should it answer?
- Should it ask clarifying questions?
- Should it use RAG?
- Should it route to a lawyer or human reviewer?
- What data asset should this failure become?

The dataset uses legal task slices: normal consultation, hard legal reasoning, risk calibration, citation grounding, adversarial traps, and counterfactual pairs. Each output goes through rubric scoring, citation verification, claim-level triage, risk routing, data routing, and release gate analysis.

I also reframed the implementation as an A0-A5 legal agent architecture:

- A0 closed-book baseline
- A1 structured legal counsel
- A2 grounded retrieval counsel
- A3 verifier-router policy layer
- A4 clarification-first intake
- A5 multi-turn legal intake agent

I ran a real Qianfan API pilot:

- 12 cases
- 5 models
- 5 workflows
- 300 real model outputs
- 300 parseable judge outputs using Qwen3.5-27B as the stable full-run judge
- 80 priority outputs human-reviewed

The main finding was not simply "which model won." A1 structured legal counsel and A4 clarification-first intake were stronger release candidates. A2/RAG was useful for source-specific tasks, but the RAG V2 pilot exposed citation-boundary issues, so grounded answers need claim-level entailment checks before product release.

## Key Numbers

| Metric                                        |                            Result |
| --------------------------------------------- | --------------------------------: |
| Real model outputs                            |                               300 |
| Judge parse success                           |                         300 / 300 |
| Priority human review rows                    |                                80 |
| Human pass / partial / fail                   |                       4 / 27 / 49 |
| Judge-human agreement                         | 92.5% on priority-enriched sample |
| Confirmed citation or evidence-support issues |                                45 |
| Human route overrides                         |                                47 |
| RAG V2 focused outputs                        |                           72 / 72 |
| RAG V2 citation-gate issue rate               |    88.1% strict release-risk gate |
| A5 multi-turn intake cases                    |                                 8 |
| A5 API pilot traces / turns                   |                           24 / 72 |
| A5 deterministic trace pass rate              |                             75.0% |
| A5 overclaim-flagged traces                   |                                 6 |

## What I Would Emphasize

The value is not that I called APIs. The value is that I turned model behavior into product and data decisions.

Examples:

- Low-risk routine consultation can use A1 structured legal counsel under a limited release gate.
- Missing-fact or risky strategy questions should use A4 clarification-first intake.
- Source-specific legal tasks require RAG, but RAG must pass citation verification.
- RAG hitting the right source is not enough; the RAG V2 pilot showed source-boundary and claim-citation failures even when expected-source recall was 100%.
- A5 multi-turn intake should be judged as a trace: prioritized questions, bad-premise challenge, bounded answer, escalation, release gate, and data route.
- Unsupported claims, fabricated citations, and unsafe drafting requests are release blockers.
- Passing high-risk answers are not badcases; they become calibration or preference examples.
- Citation failures become regression evals and source-boundary badcases.

## Honest Limitations

I would state these directly:

- The RAG corpus is controlled and still small.
- Citation verification is stronger than source-id matching, but not yet full legal entailment.
- Full-run scoring currently uses one stable judge plus human review, not a fully reliable multi-judge ensemble.
- The RAG V2 88.1% citation-gate issue rate is a strict material-claim release gate, not an overall legal-answer accuracy rate.
- The A5 75.0% pilot pass rate is still deterministic triage, not human-validated legal correctness.
- A5 still needs human calibration with the A5 rubric, especially for the 6 overclaim-flagged traces.
- The real API pilot is intentionally small, designed to prove method and product decision value rather than claim statistical superiority.

These are not fatal weaknesses. They define the next data loop.

## Next Iteration

RAG V2 is now complete as a focused pilot. Its product lesson is:

- retrieval recall can be high while release risk remains high;
- source-boundary filtering is a product requirement, not a retrieval nice-to-have;
- claim-level citation coverage must be enforced before source-specific answers are released.

The agentic next iteration is A5 calibration:

- human-calibrate the 24 completed pilot traces;
- measure material-fact elicitation, bad-premise challenge, user-behavior adaptation, and escalation timing with the A5-specific judge rubric;
- route trace failures into SFT, preference, badcase, and regression eval assets.

## Strong Closing

My takeaway is that legal AI evaluation should not stop at "Model A scored 86." For a product team, the more important questions are what the model is allowed to do, where it needs grounding, when it must ask for more facts, when it must escalate to human review, and which failures should become the next training or evaluation data. This project operationalizes that loop.
