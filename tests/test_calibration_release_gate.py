import pandas as pd
import pytest

from legal_eval_harness.calibration import build_human_review_sample, summarize_human_calibration
from legal_eval_harness.release_gate import build_release_gate
from legal_eval_harness.utils import json_dumps


def _frames():
    runs = pd.DataFrame(
        [
            {
                "run_id": "r1",
                "sample_id": "S1",
                "task_category": "consultation",
                "model_alias": "Model_A",
                "version": "V0",
                "workflow_condition": "W0",
                "workflow_name": "closed-book answer",
                "output_text": "unsafe",
                "latency_ms": 100,
                "estimated_cost": 0.01,
            },
            {
                "run_id": "r2",
                "sample_id": "S2",
                "task_category": "case_analysis",
                "model_alias": "Model_A",
                "version": "V3",
                "workflow_condition": "W3",
                "workflow_name": "risk-control workflow agent",
                "output_text": "better",
                "latency_ms": 200,
                "estimated_cost": 0.02,
            },
            {
                "run_id": "r3",
                "sample_id": "S3",
                "task_category": "document_drafting",
                "model_alias": "Model_A",
                "version": "V3",
                "workflow_condition": "W3",
                "workflow_name": "risk-control workflow agent",
                "output_text": "ok",
                "latency_ms": 120,
                "estimated_cost": 0.01,
            },
        ]
    )
    scores = pd.DataFrame(
        [
            {
                "run_id": "r1",
                "sample_id": "S1",
                "source_dataset": "pilot",
                "task_category": "consultation",
                "model_alias": "Model_A",
                "version": "V0",
                "score_rate": 0.2,
                "risk_level": "high",
                "judge_confidence": "low",
                "needs_human_review": True,
                "error_tags": json_dumps(
                    [{"coarse_error_tag": "unsafe_action_suggestion", "error_subtype": "stop_work"}]
                ),
                "judge_reason": "critical",
                "parsed_ok": True,
            },
            {
                "run_id": "r2",
                "sample_id": "S2",
                "source_dataset": "pilot",
                "task_category": "case_analysis",
                "model_alias": "Model_A",
                "version": "V3",
                "score_rate": 0.85,
                "risk_level": "low",
                "judge_confidence": "high",
                "needs_human_review": False,
                "error_tags": json_dumps([]),
                "judge_reason": "ok",
                "parsed_ok": True,
            },
            {
                "run_id": "r3",
                "sample_id": "S3",
                "source_dataset": "pilot",
                "task_category": "document_drafting",
                "model_alias": "Model_A",
                "version": "V3",
                "score_rate": 0.82,
                "risk_level": "low",
                "judge_confidence": "high",
                "needs_human_review": False,
                "error_tags": json_dumps([]),
                "judge_reason": "ok",
                "parsed_ok": True,
            },
        ]
    )
    routing = pd.DataFrame(
        [
            {
                "run_id": "r1",
                "sample_id": "S1",
                "data_route": "human_review",
                "main_error_type": "unsafe_action_suggestion",
                "route_reason": "critical",
                "priority": "P0",
            },
            {
                "run_id": "r2",
                "sample_id": "S2",
                "data_route": "eval",
                "main_error_type": "none",
                "route_reason": "holdout",
                "priority": "P2",
            },
            {
                "run_id": "r3",
                "sample_id": "S3",
                "data_route": "eval",
                "main_error_type": "none",
                "route_reason": "holdout",
                "priority": "P2",
            },
        ]
    )
    return runs, scores, routing


def test_human_review_sample_includes_critical_rows(tmp_path):
    runs, scores, routing = _frames()
    sample = build_human_review_sample(
        runs=runs,
        scores=scores,
        routing=routing,
        output_path=tmp_path / "human_review.csv",
        sample_rate=0.2,
        min_samples=1,
    )

    assert "r1" in set(sample["run_id"])
    assert sample.loc[sample["run_id"] == "r1", "critical_for_review"].item()
    assert "human_notes" in sample.columns


def test_human_review_sample_includes_citation_and_ensemble_signals(tmp_path):
    runs, scores, routing = _frames()
    citation = pd.DataFrame(
        [
            {
                "run_id": "r2",
                "citation_fidelity_label": "unsupported_claim",
                "fabricated_citation_count": 0,
                "unsupported_claim_count": 2,
                "claim_count": 3,
                "claim_checks": "[]",
            }
        ]
    )
    ensemble = pd.DataFrame(
        [
            {
                "run_id": "r3",
                "ensemble_status": "needs_human_calibration",
                "final_data_route": "human_review",
                "requires_arbitration": True,
                "requires_human_calibration": True,
                "disagreement_reasons": "route_mismatch",
            }
        ]
    )

    sample = build_human_review_sample(
        runs=runs,
        scores=scores,
        routing=routing,
        citation_verification=citation,
        ensemble_summary=ensemble,
        output_path=tmp_path / "human_review.csv",
        sample_rate=0.2,
        min_samples=1,
    )

    assert "r2" in set(sample["run_id"])
    assert "r3" in set(sample["run_id"])
    assert "human_citation_support" in sample.columns
    assert "human_route_override" in sample.columns


def test_human_review_sample_can_add_random_calibration_rows(tmp_path):
    runs, scores, routing = _frames()
    sample = build_human_review_sample(
        runs=runs,
        scores=scores,
        routing=routing,
        output_path=tmp_path / "human_review.csv",
        sample_rate=0.2,
        min_samples=1,
        random_calibration_min=2,
    )

    assert set(sample["run_id"]) == {"r1", "r2", "r3"}
    assert sample.loc[sample["run_id"] == "r1", "review_bucket"].item() == "critical_failure"
    assert set(sample.loc[sample["run_id"].isin(["r2", "r3"]), "review_bucket"]) == {"random_calibration"}


def test_human_calibration_summary_counts_reviewed_rows(tmp_path):
    reviewed = pd.DataFrame(
        [
            {
                "run_id": "r1",
                "human_pass_fail": "fail",
                "human_critical_failure": "yes",
                "human_citation_support": "unsupported",
                "human_route_override": "human_review",
                "human_data_action": "badcase",
                "judge_human_agreement": "agree",
            },
            {"run_id": "r2", "human_pass_fail": "", "judge_human_agreement": ""},
        ]
    )

    summary = summarize_human_calibration(reviewed=reviewed, output_path=tmp_path / "summary.csv")

    row = summary.iloc[0]
    assert row["completed_review_rows"] == 1
    assert row["confirmed_critical_failure_count"] == 1
    assert row["confirmed_citation_issue_count"] == 1
    assert row["judge_human_agreement_rate"] == 1.0
    assert row["judge_human_overall_triage_agreement_rate"] == 1.0
    assert row["agreement_basis"] == "legacy manually supplied judge_human_agreement labels; not reviewer IAA"


def test_release_gate_blocks_unsafe_action(tmp_path):
    runs, scores, routing = _frames()
    gate = build_release_gate(
        runs=runs,
        scores=scores,
        routing=routing,
        output_path=tmp_path / "release_gate.csv",
    )

    blocked = gate[gate["workflow_condition"] == "W0"].iloc[0]
    assert blocked["release_gate_decision"] == "blocked"
    assert blocked["release_decision"] == "blocked"
    assert "unsafe action" in blocked["blockers"]

    candidate = gate[(gate["task_category"] == "case_analysis") & (gate["workflow_condition"] == "W3")].iloc[0]
    assert candidate["release_gate_decision"] == "candidate_auto_answer"
    assert candidate["release_decision"] == "candidate_auto_answer"


def test_release_gate_blocks_group_when_response_policy_is_block(tmp_path):
    runs, scores, routing = _frames()
    runs = runs.loc[runs["run_id"] == "r2"].copy()
    scores = scores.loc[scores["run_id"] == "r2"].copy()
    routing = routing.loc[routing["run_id"] == "r2"].copy()
    routing["response_policy"] = "block"
    routing["workflow_status"] = "blocked"

    gate = build_release_gate(
        runs=runs,
        scores=scores,
        routing=routing,
        output_path=tmp_path / "release_gate.csv",
    )

    row = gate.iloc[0]
    assert row["blocked_response_rate"] == 1.0
    assert row["release_gate_decision"] == "blocked"
    assert "response rows are blocked" in row["blockers"]

    assert row["release_decision"] == "blocked"


def test_release_gate_blocks_claim_entailment_source_boundary(tmp_path):
    runs, scores, routing = _frames()
    claim_entailment = pd.DataFrame(
        [
            {
                "run_id": "r2",
                "claim_index": 1,
                "claim": "根据外部来源可以解除。",
                "reviewable_legal_claim": True,
                "entailment_label": "out_of_scope_source",
                "product_action": "source_boundary_regression",
            }
        ]
    )

    gate = build_release_gate(
        runs=runs,
        scores=scores,
        routing=routing,
        claim_entailment=claim_entailment,
        output_path=tmp_path / "release_gate.csv",
    )

    blocked = gate[(gate["task_category"] == "case_analysis") & (gate["workflow_condition"] == "W3")].iloc[0]
    assert blocked["release_decision"] == "blocked"
    assert blocked["out_of_scope_source_count"] == 1
    assert "source-boundary citation failure" in blocked["blockers"]


def test_release_gate_parses_string_false_flags(tmp_path):
    runs, scores, routing = _frames()
    scores = scores.loc[scores["run_id"] == "r2"].copy()
    runs = runs.loc[runs["run_id"] == "r2"].copy()
    routing = routing.loc[routing["run_id"] == "r2"].copy()
    scores["parsed_ok"] = "False"
    claim_entailment = pd.DataFrame(
        [
            {
                "run_id": "r2",
                "claim_index": 1,
                "claim": "结构性说明，不是可审查法律主张。",
                "reviewable_legal_claim": "False",
                "entailment_label": "not_reviewable",
            }
        ]
    )

    gate = build_release_gate(
        runs=runs,
        scores=scores,
        routing=routing,
        claim_entailment=claim_entailment,
        output_path=tmp_path / "release_gate.csv",
    )

    row = gate.iloc[0]
    assert row["parsed_ok_rate"] == 0.0
    assert row["judge_parse_failure_rate"] == 1.0
    assert row["reviewable_claim_count"] == 0


def test_release_gate_separates_reviewable_issues_from_all_claim_blockers(tmp_path):
    runs, scores, routing = _frames()
    scores = scores.loc[scores["run_id"] == "r2"].copy()
    runs = runs.loc[runs["run_id"] == "r2"].copy()
    routing = routing.loc[routing["run_id"] == "r2"].copy()
    claim_entailment = pd.DataFrame(
        [
            {
                "run_id": "r2",
                "claim_index": 1,
                "reviewable_legal_claim": True,
                "entailment_label": "no_citation",
            },
            {
                "run_id": "r2",
                "claim_index": 2,
                "reviewable_legal_claim": True,
                "entailment_label": "supported",
            },
            {
                "run_id": "r2",
                "claim_index": 3,
                "reviewable_legal_claim": True,
                "entailment_label": "partially_supported",
            },
            {
                "run_id": "r2",
                "claim_index": 4,
                "reviewable_legal_claim": False,
                "entailment_label": "out_of_scope_source",
            },
        ]
    )

    gate = build_release_gate(
        runs=runs,
        scores=scores,
        routing=routing,
        claim_entailment=claim_entailment,
        output_path=tmp_path / "release_gate.csv",
    )

    row = gate.iloc[0]
    assert row["reviewable_claim_count"] == 3
    assert row["reviewable_strict_citation_defect_count"] == 1
    assert row["reviewable_claim_needs_review_count"] == 2
    assert row["citation_gate_issue_count"] == 2
    assert row["reviewable_citation_issue_count"] == 2
    assert row["citation_gate_issue_rate"] == pytest.approx(2 / 3, abs=0.0001)
    assert row["all_claim_source_boundary_blocker_count"] == 1
    assert row["release_gate_decision"] == "blocked"


def test_human_calibration_summary_computes_reviewer_pair_metrics(tmp_path):
    reviewed = pd.DataFrame(
        [
            {
                "run_id": "r1",
                "auto_triage_label": "block",
                "reviewer_a_triage_label": "block",
                "reviewer_b_triage_label": "block",
                "adjudicated_triage_label": "block",
            },
            {
                "run_id": "r2",
                "auto_triage_label": "auto_answer",
                "reviewer_a_triage_label": "auto_answer",
                "reviewer_b_triage_label": "human_review",
                "adjudicated_triage_label": "human_review",
            },
        ]
    )

    summary = summarize_human_calibration(reviewed=reviewed, output_path=tmp_path / "summary.csv")

    row = summary.iloc[0]
    assert row["reviewer_pair_labeled_rows"] == 2
    assert row["reviewer_observed_agreement_rate"] == 0.5
    assert row["reviewer_cohen_kappa"] == pytest.approx(1 / 3, abs=0.001)
    assert row["judge_adjudicated_agreement_rate"] == 0.5
