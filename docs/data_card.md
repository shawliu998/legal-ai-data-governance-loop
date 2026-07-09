# Data Card

## Dataset Scope

This repository contains controlled legal AI evaluation data for product-boundary and data-routing experiments. The dataset covers legal consultation, case analysis, document drafting, source-limited QA, RAG citation checks, and multi-turn intake traces.

The data is pilot-scale. Results should be read as product diagnosis evidence for this repository, not as statistically significant conclusions about model quality.

## Data Sources

The evaluation inputs are controlled project materials and practice-style legal scenarios. The repository does not claim to use private user query logs, confidential case files, or production customer data.

RAG-related examples use a controlled source setting. They are intended to test whether answers stay within provided materials and cite support for material claims, not to validate a live legal retrieval system.

## Intended Use

The dataset is intended for:

- `eval`: measuring product-boundary behavior and regression risk.
- `sft`: identifying answer patterns that may be useful for supervised fine-tuning candidates.
- `preference`: creating comparison candidates for safer or more grounded responses.
- `badcase`: documenting failures that require product or data follow-up.
- `regression`: rechecking known failure modes after prompt, model, or RAG changes.
- `human_review`: routing high-risk, ambiguous, or blocker-enriched samples to manual review.

## Out of Scope

This dataset is not a legal advice service, a complete legal knowledge base, a public model ranking benchmark, or evidence that any model is suitable for production legal use.

It also does not cover every jurisdiction, legal domain, document type, or user behavior pattern.

## Privacy and Redaction

The repository does not claim to contain real private user data. If production query logs or lawyer-reviewed answer samples are introduced in a real product setting, they should be redacted before use and reviewed for privacy, confidentiality, and legal-domain sensitivity.

Fields used for evaluation should avoid unnecessary personal identifiers. Evidence packages should preserve the reasoning needed for review while minimizing sensitive content exposure.

## Legal Domain Boundary

The dataset is designed to test legal AI product behavior, including when the system should answer directly, ask for missing facts, cite grounded sources, route to human review, or block release.

It does not replace legal professional judgment. High-risk matters, jurisdiction-specific uncertainty, missing facts, and unsupported legal claims should be treated as review or escalation candidates.

## Quality Control

Evaluation inputs, gold labels, and rubric items are kept as separate artifacts to reduce leakage risk. Agents should only receive the evaluation input and any allowed context. Judge and human review steps may use gold labels and rubric items for scoring and diagnosis.

High-risk rows, blocker-enriched rows, citation/source-boundary failures, and low-confidence cases are expected to enter human review. Human review samples in this repo are used for calibration and diagnosis; they should not be treated as random population estimates.

## Data Asset Routing

Each output can be routed into one or more downstream data assets:

- `eval` for broad product-boundary coverage.
- `sft` for answer-format and behavior candidates after review.
- `preference` for pairwise comparisons between safer and weaker outputs.
- `badcase` for issue tracking and root-cause notes.
- `regression` for repeat checks after system changes.
- `human_review` for high-risk, ambiguous, unsupported, or blocker-level cases.

The routing label is a product decision aid. It does not by itself approve an answer for legal use.
