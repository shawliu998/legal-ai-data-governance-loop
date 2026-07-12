# Asset lifecycle v1

## Scope

This protocol governs the first flywheel release only: five SFT, five preference, and five disclosed
same-source regression bug reproductions. It does not alter the existing meanings of `response_policy`, `workflow_status`, or
`data_asset_routes`. Storage is append-only JSONL plus release CSV/YAML; there is no database or UI.

## Lifecycle

```text
proposed -> correction_drafting -> ai_review_pending
         -> adjudication_pending (only when A/B conflict)
         -> qa_pending -> expert_review_pending
         -> accepted | rework_required | rejected
```

Only `AssetService` may change `asset_status`. Rework returns to `correction_drafting`. Accepted and
rejected are terminal in v1. Dataset membership and regression execution are independent status axes.

## Acceptance gate

An asset can be accepted only when it has a corrected answer, isolated reviewer A and B events, an AI
proposed adjudication when those decisions conflict, passed PII/duplicate/source/contamination/law-date/
type-specific QA, and an explicit approval event from a legal expert in the `final_expert` role. AI
adjudication can never accept an asset.

Review, adjudication, QA, and final-expert events are valid only when all four lineage values match the
latest correction: correction ID, correction revision, corrected-answer hash, and source-snapshot ID.
Evidence from a superseded revision cannot advance the state machine.

An included membership additionally requires an accepted asset, release id, and split. Regression
execution additionally requires a regression asset, included membership, non-empty assertions, and a
real rerun id. Regression/eval assets are not training eligible. Membership identity is the composite
of release ID, asset ID, and split, so an accepted asset may be reused in a later release.

Train/test contamination checks operate across asset types and compare source case, source snapshot,
normalized prompt hash, and counterfactual family. The v0.1 same-source regressions are assigned the
`bug_reproduction` split rather than `test`; no independent test-set claim is made.

## Review independence and public wording

Reviewer A focuses on legal conclusion, material facts, unsafe action advice, limitation periods,
response policy, and asset type. Reviewer B focuses on unsupported claims, certainty, citation support,
clarification, human escalation, and publishability. They use isolated contexts and do not see the
router, `human_*` labels, historical reviews, expert decisions, or each other's result. Every blind-v2
event records model, prompt version, context id, timestamps, raw-output evidence path, input/output
hashes, correction id/revision, source snapshot id, and corrected-answer hash. Historical legacy-v1
reviews that received prior human signals remain preserved but are excluded from corrected metrics.

Final expert approval is additionally bound to the exact correction text and original submitted review
CSV through an `ExpertApprovalBinding`. Source snapshot changes are represented by version events;
reconstructed versions are explicitly marked rather than presented as originally captured events.

External wording for this pilot: legacy-v1 A/B pre-reviews preceded legal-expert final review but had
prior-label contamination, which is disclosed and excluded from corrected metrics. Frozen accepted
texts were subsequently re-audited using label-isolated blind-v2 A/B and conflict consolidation. Every
formally released asset is still bound to an item-level legal-PhD approval. Until that approval exists,
the repository must call records candidates or a review bundle, never accepted assets.
