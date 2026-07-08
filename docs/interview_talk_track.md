# Interview Talk Track

## 30-Second Version

I built a legal AI product-boundary eval and data governance harness. Instead of ranking models by average score, it evaluates whether a legal AI product should answer, ask clarifying questions, use grounded sources, route to human review, or block release. I ran a real Qianfan API pilot across ERNIE 5.0, DeepSeek V4 Pro, Qwen3.5-27B, GLM-5.2, and Kimi K2.6, then human-reviewed 80 priority outputs. The output is not just scores; it is model-workflow routing policy, release gates, and next-round data production actions.

## 2-Minute Version

The project started from a practical product question: in legal AI, average model score is not enough. A model can sound fluent and still fabricate a citation, overstate litigation chances, miss a need for human review, or use sources outside the allowed materials.

So I designed the eval around product decisions:

- Can the model answer?
- Should it answer?
- Should it ask clarifying questions?
- Should it use RAG?
- Should it route to a lawyer or human reviewer?
- What data asset should this failure become?

The dataset uses legal task slices: normal consultation, hard legal reasoning, risk calibration, citation grounding, adversarial traps, and counterfactual pairs. Each output goes through rubric scoring, citation verification, risk routing, data routing, and release gate analysis.

I ran a real Qianfan API pilot:

- 12 cases
- 5 models
- 5 workflows
- 300 real model outputs
- 300 parseable judge outputs using Qwen3.5-27B as the stable full-run judge
- 80 priority outputs human-reviewed

The main finding was not simply "which model won." W1 structured prompt and W5 clarification-first were stronger release candidates. Current RAG/verifier workflows were useful but exposed citation-boundary issues, so RAG needs claim-level entailment checks before product release.

## Key Numbers

| Metric | Result |
| --- | ---: |
| Real model outputs | 300 |
| Judge parse success | 300 / 300 |
| Priority human review rows | 80 |
| Human pass / partial / fail | 4 / 27 / 49 |
| Judge-human agreement | 92.5% on priority-enriched sample |
| Confirmed citation or evidence-support issues | 45 |
| Human route overrides | 47 |

## What I Would Emphasize

The value is not that I called APIs. The value is that I turned model behavior into product and data decisions.

Examples:

- Low-risk routine consultation can use W1 structured prompt under a limited release gate.
- Missing-fact or risky strategy questions should use W5 clarification-first.
- Source-specific legal tasks require RAG, but RAG must pass citation verification.
- Unsupported claims, fabricated citations, and unsafe drafting requests are release blockers.
- Passing high-risk answers are not badcases; they become calibration or preference examples.
- Citation failures become regression evals and source-boundary badcases.

## Honest Limitations

I would state these directly:

- The RAG corpus is controlled and still small.
- Citation verification is stronger than source-id matching, but not yet full legal entailment.
- Full-run scoring currently uses one stable judge plus human review, not a fully reliable multi-judge ensemble.
- The real API pilot is intentionally small, designed to prove method and product decision value rather than claim statistical superiority.

These are not fatal weaknesses. They define the next data loop.

## Next Iteration

The next iteration is RAG V2:

- expand the corpus with precise legal, contract, policy, and case-rule sources;
- add claim-level citation entailment;
- separate retrieval quality from generation quality;
- rerun a focused citation/document API pilot;
- update release gates based on human-calibrated citation labels.

## Strong Closing

My takeaway is that legal AI evaluation should not stop at "Model A scored 86." For a product team, the more important questions are what the model is allowed to do, where it needs grounding, when it must ask for more facts, when it must escalate to human review, and which failures should become the next training or evaluation data. This project operationalizes that loop.
