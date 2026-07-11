import json
from pathlib import Path

import pandas as pd
import yaml

from legal_eval_harness.a5_multiturn import (
    _has_overclaim,
    load_a5_cases,
    run_a5_multiturn_smoke,
    validate_a5_cases,
)


ROOT = Path(__file__).resolve().parents[1]


def test_a5_case_file_validates():
    cases = load_a5_cases(ROOT / "data/eval_sets/legal_agent_multiturn_intake_pilot_v1.jsonl")
    assert len(cases) == 8
    assert validate_a5_cases(cases) == []
    for case in cases:
        assert "expected_release_policy" not in case
        assert "expected_data_route" not in case
        assert "human_review" not in case["expected_data_asset_routes"]
        assert case["expected_trace_review_recommendation"] in {
            "blocked",
            "human_review_required",
            "candidate_limited_release",
        }


def test_a5_lexical_overclaim_does_not_treat_guarantee_law_terms_as_promises():
    text = "本案涉及保证合同、一般保证、保证期间、保证人的抗辩权和必然因果关系。"

    assert _has_overclaim(text) is False


def test_a5_lexical_overclaim_flags_outcome_promise_but_respects_negation():
    assert _has_overclaim("我保证胜诉，并保证拿到赔偿。") is True
    assert _has_overclaim("本案必然胜诉。") is True
    assert _has_overclaim("律师不能保证胜诉，也不应承诺一定能获赔。") is False
    assert _has_overclaim('我无法告诉你“这些证据一定能赢”或“对方一定要赔多少”。') is False
    assert _has_overclaim('我不能替你下“他一定违法”或“你一定能拿到赔偿”的结论。') is False
    assert _has_overclaim("不能承诺所有案件，但本案保证胜诉。") is True


def test_a5_multiturn_smoke_writes_redacted_artifacts(tmp_path):
    config = {
        "models": [
            {
                "alias": "mock_model",
                "vendor": "Mock",
                "family": "Mock",
                "provider": "mock",
                "model": "mock",
            }
        ],
        "generation": {"temperature": 0.0, "max_output_tokens": 400},
    }

    result = run_a5_multiturn_smoke(
        cases_path=ROOT / "data/eval_sets/legal_agent_multiturn_intake_pilot_v1.jsonl",
        config=config,
        output_dir=tmp_path,
        mode="mock",
        case_ids=["A5-INTAKE-001"],
        model_aliases=["mock_model"],
    )

    metrics = result["trace_metrics_summary"].set_index("metric")
    assert metrics.loc["traces", "value"] == 1
    assert metrics.loc["turns", "value"] == 3
    assert "trace_pass_rate" not in metrics.index
    assert metrics.loc["human_calibration_status", "value"] == "pending"
    assert not (tmp_path / "trace_log.jsonl").exists()
    raw_trace_path = tmp_path.parent / f"{tmp_path.name}_raw" / "trace_log.jsonl"
    assert raw_trace_path.exists()
    assert (tmp_path.parent / f"{tmp_path.name}_raw" / "turn_log.csv").exists()
    raw_trace = json.loads(raw_trace_path.read_text(encoding="utf-8").splitlines()[0])
    assert raw_trace["expected_trace_review_recommendation"] == "human_review_required"
    assert raw_trace["expected_data_asset_routes"] == ["sft", "regression"]
    assert "expected_release_policy" not in raw_trace
    assert "expected_data_route" not in raw_trace
    assert "release_decision" not in raw_trace["evaluation"]
    assert "trace_pass" not in raw_trace["evaluation"]
    assert "overclaim_detected" not in raw_trace["evaluation"]
    assert (tmp_path / "redacted_trace_example.md").exists()
    assert (tmp_path / "human_trace_calibration_template.csv").exists()
    redacted = pd.read_csv(tmp_path / "redacted_trace_samples.csv")
    assert "agent_message" not in redacted.columns
    assert "lexical_overclaim_flag" in redacted.columns
    assert "trace_review_recommendation" in redacted.columns
    assert "release_decision" not in redacted.columns
    assert redacted["turn_output_hashes"].item()
    calibration = pd.read_csv(tmp_path / "human_trace_calibration_template.csv")
    assert "human_escalation_timing_0_2" in calibration.columns
    assert {
        "reviewer_a_triage_label",
        "reviewer_b_triage_label",
        "adjudicated_triage_label",
        "adjudication_mode",
    }.issubset(calibration.columns)
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "No model behavior pass rate is reported" in readme
    manifest = yaml.safe_load((tmp_path / "artifact_manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "2.0"
    assert manifest["run_stage"] == "pilot"
    assert manifest["current_portfolio_evidence"] is True
    assert manifest["human_calibration_status"] == "pending"
    assert manifest["model_behavior_pass_rate_reported"] is False
    assert "human_data_asset_routes" in calibration.columns
    assert "human_data_route" not in calibration.columns
    assert {"human_response_policy", "human_workflow_status"}.issubset(calibration.columns)
