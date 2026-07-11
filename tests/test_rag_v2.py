from pathlib import Path

import pandas as pd

from legal_eval_harness.rag_v2 import build_rag_v2_report


ROOT = Path(__file__).resolve().parents[1]


def test_rag_v2_report_writes_lightweight_artifacts(tmp_path):
    run_id = "RUN-LPB-CITE-001-model_a-V4"
    runs = pd.DataFrame(
        [
            {
                "run_id": run_id,
                "sample_id": "LPB-CITE-001",
                "task_category": "case_analysis",
                "model_alias": "model_a",
                "model_vendor": "Vendor",
                "model_family": "Family",
                "version": "V4",
                "workflow_condition": "W2",
                "workflow_name": "provided-context grounded answer",
                "output_text": "根据 [CONTRACT-001]，逾期发货可主张违约金。",
                "latency_ms": 100,
                "estimated_cost": 0.01,
            }
        ]
    )
    retrieval = pd.DataFrame(
        [
            {
                "run_id": run_id,
                "sample_id": "LPB-CITE-001",
                "model_alias": "model_a",
                "version": "V4",
                "workflow_condition": "W2",
                "retrieved_source_ids": '["CONTRACT-001", "PLATFORM-001"]',
                "expected_source_ids": '["CONTRACT-001", "PLATFORM-001"]',
                "retrieval_status": "hit",
            }
        ]
    )
    citation = pd.DataFrame(
        [
            {
                "run_id": run_id,
                "citation_count": 1,
                "valid_citation_count": 1,
                "fabricated_citation_count": 0,
                "unsupported_claim_count": 0,
                "citation_fidelity_label": "citation_supported",
            }
        ]
    )
    claims = pd.DataFrame(
        [
            {
                "run_id": run_id,
                "sample_id": "LPB-CITE-001",
                "model_alias": "model_a",
                "version": "V4",
                "workflow_condition": "W2",
                "claim_index": 1,
                "claim": "逾期发货可主张违约金",
                "reviewable_legal_claim": True,
                "cited_source_ids": '["CONTRACT-001"]',
                "entailment_label": "supported",
                "product_action": "pass_citation_gate",
            },
            {
                "run_id": run_id,
                "sample_id": "LPB-CITE-001",
                "model_alias": "model_a",
                "version": "V4",
                "workflow_condition": "W2",
                "claim_index": 2,
                "claim": "结构性片段引用了范围外来源",
                "reviewable_legal_claim": False,
                "cited_source_ids": '["OUTSIDE-001"]',
                "entailment_label": "out_of_scope_source",
                "product_action": "source_boundary_regression",
            },
        ]
    )
    scores = pd.DataFrame(
        [
            {
                "run_id": run_id,
                "score_rate": 0.9,
                "needs_human_review": False,
            }
        ]
    )
    routing = pd.DataFrame([{"run_id": run_id, "data_route": "eval_holdout"}])

    for name, frame in {
        "runs.csv": runs,
        "retrieval.csv": retrieval,
        "citation.csv": citation,
        "claims.csv": claims,
        "scores.csv": scores,
        "routing.csv": routing,
    }.items():
        frame.to_csv(tmp_path / name, index=False)

    result = build_rag_v2_report(
        runs_path=tmp_path / "runs.csv",
        retrieval_path=tmp_path / "retrieval.csv",
        citation_path=tmp_path / "citation.csv",
        claim_entailment_path=tmp_path / "claims.csv",
        judge_scores_path=tmp_path / "scores.csv",
        routing_path=tmp_path / "routing.csv",
        cases_jsonl=ROOT / "data/eval_sets/legal_product_boundary_pilot_v1.jsonl",
        output_dir=tmp_path / "report",
        focus_cases=["LPB-CITE-001"],
        focus_versions=["V4"],
    )

    assert result["metrics_summary"].set_index("metric").loc["api_run_records", "value"] == 1
    metrics = result["metrics_summary"].set_index("metric")["value"]
    assert metrics.loc["reviewable_claim_rows"] == 1
    assert metrics.loc["reviewable_claim_needs_review_rows"] == 0
    assert metrics.loc["reviewable_claim_needs_review_rate"] == 0
    assert metrics.loc["all_claim_source_boundary_blocker_rows"] == 1
    assert metrics.loc["all_claim_source_boundary_blocker_rate"] == 0.5
    assert not {
        "reviewable_claim_citation_issue_rows",
        "citation_gate_issue_rows",
        "claim_release_blocker_rate",
    }.intersection(metrics.index)
    source_summary = pd.read_csv(tmp_path / "report/source_boundary_summary.csv")
    assert source_summary["source_boundary_precision"].item() == 1.0
    redacted = pd.read_csv(tmp_path / "report/redacted_sample_outputs_20.csv")
    assert "output_text" not in redacted.columns
    assert not {"reviewable_citation_issue_count", "citation_gate_issue_count", "claim_release_blocker_count"}.intersection(
        redacted.columns
    )
    assert redacted["output_sha256_12"].item()
