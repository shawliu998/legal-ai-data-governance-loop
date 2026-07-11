import pandas as pd
import pytest

from legal_eval_harness.router import apply_review_adjudications, route_scores
from legal_eval_harness.schemas import DATA_ROUTES, RoutingDecision
from legal_eval_harness.utils import json_dumps, json_loads_or_none


def test_router_uses_fixed_route_enum(tmp_path):
    scores = pd.DataFrame(
        [
            {
                "sample_id": "L-001",
                "run_id": "RUN-L-001-Model_A-V0",
                "error_tags": json_dumps(
                    [{"coarse_error_tag": "overclaim", "error_subtype": "premature_conclusion"}]
                ),
                "risk_level": "medium",
                "judge_confidence": "medium",
                "needs_human_review": False,
                "score_rate": 0.55,
                "parsed_ok": True,
            },
            {
                "sample_id": "L-002",
                "run_id": "RUN-L-002-Model_A-V0",
                "error_tags": json_dumps(
                    [{"coarse_error_tag": "fabricated_citation", "error_subtype": "fake_article"}]
                ),
                "risk_level": "high",
                "judge_confidence": "low",
                "needs_human_review": True,
                "score_rate": 0.2,
                "parsed_ok": True,
            },
        ]
    )

    routed = route_scores(judge_scores=scores, output_path=tmp_path / "routing.csv")
    assert set(routed["data_route"]).issubset(set(DATA_ROUTES))
    assert routed.loc[routed["sample_id"] == "L-002", "data_route"].item() == "human_review"
    critical = routed.loc[routed["sample_id"] == "L-002"].iloc[0]
    assert critical["workflow_status"] == "blocked"
    assert critical["response_policy"] == "block"
    assert critical["release_decision"] == "block"
    assert "regression" in critical["data_asset_routes"]
    assert critical["main_error_type"] == "fabricated_citation"
    assert not bool(critical["gold_approved"])


def test_router_does_not_treat_string_false_as_review_flag(tmp_path):
    scores = pd.DataFrame(
        [
            {
                "sample_id": "L-003",
                "run_id": "RUN-L-003-Model_A-V1",
                "error_tags": json_dumps([]),
                "risk_level": "low",
                "judge_confidence": "high",
                "needs_human_review": "False",
                "score_rate": 0.9,
                "parsed_ok": "True",
                "citation_required": "False",
            },
        ]
    )

    routed = route_scores(judge_scores=scores, output_path=tmp_path / "routing.csv")

    row = routed.iloc[0]
    assert row["data_route"] == "eval"
    assert row["workflow_status"] == "released"
    assert row["response_policy"] == "auto_answer"
    assert bool(row["reusable_as_gold_sample"]) is False


def test_router_covers_all_response_policies_and_serializes_only_at_csv_boundary(tmp_path):
    base = {
        "source_dataset": "pilot",
        "task_category": "consultation",
        "model_alias": "Model_A",
        "version": "V1",
        "score_rate": 0.9,
        "risk_level": "low",
        "judge_confidence": "high",
        "needs_human_review": False,
        "parsed_ok": True,
    }
    scores = pd.DataFrame(
        [
            dict(base, sample_id="AUTO", run_id="r-auto", error_tags=[], gold_approved=True),
            dict(base, sample_id="GROUND", run_id="r-ground", error_tags=[]),
            dict(
                base,
                sample_id="CLARIFY",
                run_id="r-clarify",
                error_tags=[{"coarse_error_tag": "missing_facts", "error_subtype": "identity"}],
            ),
            dict(
                base,
                sample_id="REVIEW",
                run_id="r-review",
                error_tags=[],
                risk_level="high",
                needs_human_review=True,
            ),
            dict(
                base,
                sample_id="BLOCK",
                run_id="r-block",
                error_tags=[
                    {"coarse_error_tag": "unsafe_action_suggestion", "error_subtype": "evidence_destruction"}
                ],
                gold_approved=True,
            ),
        ]
    )
    runs = pd.DataFrame(
        [
            {"run_id": "r-auto", "rag_enabled": False, "run_status": "ok"},
            {"run_id": "r-ground", "rag_enabled": "True", "rag_source_ids": '["LAW-1"]', "run_status": "ok"},
            {"run_id": "r-clarify", "rag_enabled": False, "run_status": "ok"},
            {"run_id": "r-review", "rag_enabled": False, "run_status": "ok"},
            {"run_id": "r-block", "rag_enabled": False, "run_status": "ok"},
        ]
    )
    output = tmp_path / "routing.csv"

    routed = route_scores(judge_scores=scores, runs=runs, output_path=output)

    policies = routed.set_index("sample_id")["response_policy"].to_dict()
    assert policies == {
        "AUTO": "auto_answer",
        "GROUND": "grounded_answer",
        "CLARIFY": "clarify",
        "REVIEW": "human_review",
        "BLOCK": "block",
    }
    assert routed.set_index("sample_id")["workflow_status"].to_dict() == {
        "AUTO": "released",
        "GROUND": "released",
        "CLARIFY": "released",
        "REVIEW": "pending_review",
        "BLOCK": "blocked",
    }
    assert all(isinstance(value, list) for value in routed["error_tags"])
    assert all(isinstance(value, list) for value in routed["data_asset_routes"])
    for row in routed.to_dict("records"):
        RoutingDecision(**row)

    serialized = pd.read_csv(output)
    assert isinstance(json_loads_or_none(serialized.loc[0, "error_tags"]), list)
    assert isinstance(json_loads_or_none(serialized.loc[0, "data_asset_routes"]), list)
    gold = routed.set_index("sample_id")["gold_approved"].to_dict()
    # Initial routing cannot approve gold even when an upstream row contains a
    # gold-like flag; only apply_review_adjudications may grant it.
    assert gold["AUTO"] is False
    assert gold["BLOCK"] is False
    assert routed.loc[routed["sample_id"] == "BLOCK", "requires_correction"].item()


def test_router_blocks_empty_output_subtype_without_run_log_join(tmp_path):
    scores = pd.DataFrame(
        [
            {
                "sample_id": "EMPTY",
                "run_id": "r-empty",
                "error_tags": [
                    {"coarse_error_tag": "needs_human_review", "error_subtype": "empty_model_output"}
                ],
                "risk_level": "high",
                "judge_confidence": "low",
                "needs_human_review": True,
                "score_rate": 0,
                "parsed_ok": True,
            }
        ]
    )

    routed = route_scores(judge_scores=scores, output_path=tmp_path / "routing.csv")

    assert routed.iloc[0]["response_policy"] == "block"
    assert routed.iloc[0]["workflow_status"] == "blocked"
    assert not bool(routed.iloc[0]["gold_approved"])


def test_review_adjudication_enforces_transitions_correction_and_gold_gates(tmp_path):
    scores = pd.DataFrame(
        [
            {
                "sample_id": sample_id,
                "run_id": run_id,
                "error_tags": [],
                "risk_level": "high",
                "judge_confidence": "low",
                "needs_human_review": True,
                "score_rate": 0.8,
                "parsed_ok": True,
            }
            for sample_id, run_id in [
                ("APPROVE", "r-approve"),
                ("REJECT", "r-reject"),
                ("REVIEWED", "r-reviewed"),
            ]
        ]
    )
    routing = route_scores(judge_scores=scores, output_path=tmp_path / "initial.csv")
    adjudications = pd.DataFrame(
        [
            {
                "run_id": "r-approve",
                "adjudicated_triage_label": "auto_answer",
                "reviewer_approved": True,
                "correction_completed": True,
                "gold_approved": True,
                "adjudication_mode": "consensus",
            },
            {
                "run_id": "r-reject",
                "adjudicated_triage_label": "block",
                "reviewer_approved": False,
                "correction_completed": False,
            },
            {
                "run_id": "r-reviewed",
                "adjudicated_triage_label": "human_review",
                "reviewer_approved": False,
                "correction_completed": False,
            },
        ]
    )

    updated = apply_review_adjudications(
        routing=routing,
        adjudications=adjudications,
        output_path=tmp_path / "adjudicated.csv",
    ).set_index("run_id")

    assert updated.loc["r-approve", "workflow_status"] == "released"
    assert updated.loc["r-approve", "response_policy"] == "auto_answer"
    assert not bool(updated.loc["r-approve", "requires_correction"])
    assert bool(updated.loc["r-approve", "gold_approved"])
    assert updated.loc["r-reject", "workflow_status"] == "blocked"
    assert not bool(updated.loc["r-reject", "gold_approved"])
    assert updated.loc["r-reviewed", "workflow_status"] == "reviewed"
    assert not bool(updated.loc["r-reviewed", "gold_approved"])

    written = pd.read_csv(tmp_path / "adjudicated.csv")
    assert isinstance(json_loads_or_none(written.iloc[0]["data_asset_routes"]), list)


def test_review_adjudication_rejects_release_before_required_correction(tmp_path):
    routing = pd.DataFrame(
        [
            {
                "run_id": "r1",
                "workflow_status": "pending_review",
                "response_policy": "human_review",
                "release_decision": "human_review",
                "data_route": "human_review",
                "data_asset_routes": ["badcase"],
                "error_tags": [],
                "candidate_for_reuse": True,
                "requires_correction": True,
                "gold_approved": False,
                "reusable_as_gold_sample": False,
            }
        ]
    )
    adjudications = pd.DataFrame(
        [
            {
                "run_id": "r1",
                "adjudicated_triage_label": "auto_answer",
                "target_workflow_status": "released",
                "reviewer_approved": True,
                "correction_completed": False,
                "gold_approved": True,
            }
        ]
    )

    with pytest.raises(ValueError, match="correction completion"):
        apply_review_adjudications(routing=routing, adjudications=adjudications)
