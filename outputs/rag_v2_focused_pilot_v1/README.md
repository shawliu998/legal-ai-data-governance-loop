# RAG V2 Focused Pilot Evidence Package

This directory contains a lightweight evidence package for the RAG V2 focused pilot.

The pilot focuses on source-limited legal QA and document-interpretation cases. It separates retrieval quality from answer quality, then turns citation and claim failures into product release-gate and data-production signals.

## Scope

- Focus cases: 8
- Model-workflow API run records analyzed: 72
- RAG retrieval rows: 24
- Claim rows analyzed: 1766
- Strict citation-defect flag rate: 0.881
- Claim-support needs-review rate: 0.9381
- All-claim source-boundary blocker count: 75
- All-claim source-boundary blocker rate: 0.0425

## Included

- `metrics_summary.csv`: high-level RAG V2 metrics.
- `workflow_comparison.csv`: workflow-level quality and risk comparison.
- `model_workflow_summary.csv`: model-workflow deployment signals.
- `failure_taxonomy.csv`: failure labels and data-routing actions.
- `source_boundary_summary.csv`: retrieval source-boundary and expected-source checks.
- `redacted_sample_outputs_20.csv`: representative rows with output length and hash only.
- `artifact_manifest.yaml`: machine-readable manifest and caveats.

## Caveats

- This is a focused citation-grounding pilot, not a full legal knowledge-base benchmark.
- Claim entailment labels are deterministic triage signals, not final legal conclusions.
- Qwen judge scores, if present, are baseline signals and should not be treated as final model rankings.
- Full raw model outputs remain local/ignored; this package commits summaries and redacted samples only.
