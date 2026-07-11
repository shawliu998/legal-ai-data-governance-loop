import pandas as pd

from legal_eval_harness.aggregator import build_executive_dashboard
from legal_eval_harness.utils import json_dumps


def test_aggregation_computes_v0_v3_delta(tmp_path):
    runs = pd.DataFrame(
        [
            {
                "run_id": "r1",
                "sample_id": "L-001",
                "source_dataset": "self_authored_core",
                "task_category": "consultation",
                "model_alias": "Model_A",
                "version": "V0",
                "output_text": "bad",
                "output_length": 3,
            },
            {
                "run_id": "r2",
                "sample_id": "L-001",
                "source_dataset": "self_authored_core",
                "task_category": "consultation",
                "model_alias": "Model_A",
                "version": "V3",
                "output_text": "better",
                "output_length": 6,
            },
        ]
    )
    tags = json_dumps([{"coarse_error_tag": "missing_facts", "error_subtype": "x"}])
    scores = pd.DataFrame(
        [
            {
                "run_id": "r1",
                "sample_id": "L-001",
                "source_dataset": "self_authored_core",
                "task_category": "consultation",
                "model_alias": "Model_A",
                "version": "V0",
                "score_rate": 0.4,
                "risk_level": "high",
                "needs_human_review": True,
                "error_tags": tags,
            },
            {
                "run_id": "r2",
                "sample_id": "L-001",
                "source_dataset": "self_authored_core",
                "task_category": "consultation",
                "model_alias": "Model_A",
                "version": "V3",
                "score_rate": 0.7,
                "risk_level": "medium",
                "needs_human_review": False,
                "error_tags": tags,
            },
        ]
    )
    routing = pd.DataFrame(
        [
            {
                "run_id": "r1",
                "sample_id": "L-001",
                "source_dataset": "self_authored_core",
                "task_category": "consultation",
                "model_alias": "Model_A",
                "version": "V0",
                "main_error_type": "missing_facts",
                "risk_level": "high",
                "data_route": "human_review",
                "priority": "P0",
                "route_reason": "review",
                "route_subtype": "x",
            },
            {
                "run_id": "r2",
                "sample_id": "L-001",
                "source_dataset": "self_authored_core",
                "task_category": "consultation",
                "model_alias": "Model_A",
                "version": "V3",
                "main_error_type": "missing_facts",
                "risk_level": "medium",
                "data_route": "sft",
                "priority": "P1",
                "route_reason": "train",
                "route_subtype": "x",
            },
        ]
    )

    dashboard = build_executive_dashboard(
        runs=runs,
        scores=scores,
        routing=routing,
        output_path=tmp_path / "dashboard.xlsx",
    )

    assert dashboard["avg_score_delta"] == 0.3
    assert dashboard["human_review_queue_size"] == 1
    assert dashboard["total_api_run_rows"] == 2
    assert dashboard["nonempty_answer_count"] == 2
    assert dashboard["empty_answer_count"] == 0
