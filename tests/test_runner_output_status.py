from pathlib import Path

from legal_eval_harness.io_excel import load_dataset
from legal_eval_harness.judge import run_judge
from legal_eval_harness.llm_client import LLMClient
from legal_eval_harness.runner import normalize_run_output_statuses, run_models
from legal_eval_harness.utils import json_loads_or_none


ROOT = Path(__file__).resolve().parents[1]


def _single_run_config() -> dict:
    return {
        "models": [
            {
                "alias": "qianfan_mock",
                "vendor": "Baidu Qianfan",
                "family": "Test",
                "provider": "openai_compatible",
                "model": "test-model",
            }
        ],
        "run_plan": {
            "full_samples": ["LPB-CITE-003"],
            "full_versions": ["V0"],
            "deep_samples": [],
        },
    }


def test_normalize_run_output_statuses_migrates_legacy_ok_rows():
    import pandas as pd

    legacy = pd.DataFrame(
        [
            {"run_id": "nonempty", "output_text": "回答", "run_status": "ok", "error_message": ""},
            {"run_id": "empty", "output_text": "", "run_status": "ok", "error_message": ""},
            {"run_id": "failed", "output_text": "", "run_status": "failed", "error_message": "timeout"},
        ]
    )

    migrated = normalize_run_output_statuses(legacy).set_index("run_id")

    assert migrated.loc["nonempty", "run_status"] == "ok"
    assert migrated.loc["nonempty", "api_call_status"] == "completed"
    assert migrated.loc["empty", "run_status"] == "empty_output"
    assert migrated.loc["empty", "content_status"] == "empty"
    assert migrated.loc["empty", "api_call_status"] == "completed"
    assert migrated.loc["failed", "run_status"] == "failed"
    assert migrated.loc["failed", "content_status"] == "not_available"


def test_run_models_distinguishes_completed_empty_answer_from_api_failure(tmp_path, monkeypatch):
    def empty_answer(self, **kwargs):
        return "   ", {
            "latency_ms": 12,
            "input_tokens": 10,
            "output_tokens": 0,
            "total_tokens": 10,
            "estimated_cost": 0.0,
            "cost_currency": "CNY",
            "usage_source": "api_usage",
        }

    monkeypatch.setattr(LLMClient, "generate_with_metadata", empty_answer)
    bundle = load_dataset(ROOT / "data/product_boundary_pilot/dataset_manifest.yaml")

    runs = run_models(
        bundle=bundle,
        config=_single_run_config(),
        mode="api",
        output_path=tmp_path / "model_run_log.csv",
        prompt_dir=ROOT / "prompts",
    )

    row = runs.iloc[0]
    assert row["api_call_status"] == "completed"
    assert row["content_status"] == "empty"
    assert not row["has_nonempty_output"]
    assert row["run_status"] == "empty_output"
    assert row["output_text"] == ""
    assert "empty answer content" in row["error_message"]

    scores = run_judge(
        runs=runs,
        bundle=bundle,
        config=_single_run_config(),
        mode="api",
        output_path=tmp_path / "judge_scores.csv",
        prompt_dir=ROOT / "prompts",
    )
    score = scores.iloc[0]
    error_tags = json_loads_or_none(score["error_tags"])
    assert error_tags[0]["error_subtype"] == "empty_model_output"
    assert "empty answer content" in score["judge_reason"]
    assert score["needs_human_review"]


def test_run_models_marks_nonempty_answer_as_normal_content(tmp_path, monkeypatch):
    def nonempty_answer(self, **kwargs):
        return "条件化法律分析。", {
            "latency_ms": 12,
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "estimated_cost": 0.0,
            "cost_currency": "CNY",
            "usage_source": "api_usage",
        }

    monkeypatch.setattr(LLMClient, "generate_with_metadata", nonempty_answer)
    bundle = load_dataset(ROOT / "data/product_boundary_pilot/dataset_manifest.yaml")

    runs = run_models(
        bundle=bundle,
        config=_single_run_config(),
        mode="api",
        output_path=tmp_path / "model_run_log.csv",
        prompt_dir=ROOT / "prompts",
    )

    row = runs.iloc[0]
    assert row["api_call_status"] == "completed"
    assert row["content_status"] == "nonempty"
    assert row["has_nonempty_output"]
    assert row["run_status"] == "ok"
