from pathlib import Path

import pandas as pd

from legal_eval_harness.config import load_config
from legal_eval_harness.io_excel import load_dataset
from legal_eval_harness.judge_ensemble import run_judge_ensemble


ROOT = Path(__file__).resolve().parents[1]


def test_judge_ensemble_excludes_self_eval_and_writes_outputs(tmp_path):
    config = load_config(ROOT / "configs/pilots/qianfan_product_boundary_runnable.yaml")
    bundle = load_dataset(
        ROOT / "data/product_boundary_pilot/dataset_manifest.yaml",
        jurisdiction="中国大陆",
        law_snapshot_date="2026-07-08",
        legal_advice_boundary="仅用于测试。",
    )
    runs = pd.DataFrame(
        [
            {
                "run_id": "RUN-LPB-NORMAL-001-qianfan_deepseek_v4_pro-V1",
                "sample_id": "LPB-NORMAL-001",
                "source_dataset": "legal_product_boundary_pilot_v1",
                "task_category": "consultation",
                "model_alias": "qianfan_deepseek_v4_pro",
                "model_vendor": "DeepSeek",
                "model_family": "DeepSeek V4 Pro",
                "model_name": "deepseek-v4-pro",
                "version": "V1",
                "output_text": "mock answer",
                "run_status": "ok",
            },
            {
                "run_id": "RUN-LPB-NORMAL-002-qianfan_qwen35_27b-V1",
                "sample_id": "LPB-NORMAL-002",
                "source_dataset": "legal_product_boundary_pilot_v1",
                "task_category": "consultation",
                "model_alias": "qianfan_qwen35_27b",
                "model_vendor": "Alibaba",
                "model_family": "Qwen3.5-27B",
                "model_name": "qwen3.5-27b",
                "version": "V1",
                "output_text": "mock answer",
                "run_status": "ok",
            },
        ]
    )

    result = run_judge_ensemble(
        runs=runs,
        bundle=bundle,
        config=config,
        mode="mock",
        output_dir=tmp_path,
        prompt_dir=ROOT / "prompts",
    )

    scores = result["scores"]
    deepseek_answer_scores = scores[scores["answer_model_alias"] == "qianfan_deepseek_v4_pro"]
    assert "judge_deepseek_v4_pro" not in set(deepseek_answer_scores["judge_model_alias"])
    assert "judge_glm_52" in set(deepseek_answer_scores["judge_model_alias"])
    assert "judge_kimi_k26" in set(deepseek_answer_scores["judge_model_alias"])

    qwen_answer_scores = scores[
        (scores["answer_model_alias"] == "qianfan_qwen35_27b") & (scores["judge_role"] == "primary")
    ]
    assert {"judge_deepseek_v4_pro", "judge_glm_52"} == set(qwen_answer_scores["judge_model_alias"])

    assert "requires_arbitration" in result["disagreements"].columns
    assert "primary_response_policies" in result["disagreements"].columns
    assert "final_response_policy" in result["summary"].columns
    assert "final_data_route" in result["summary"].columns
    assert (tmp_path / "judge_ensemble_scores.csv").exists()
    assert (tmp_path / "judge_disagreements.csv").exists()
    assert (tmp_path / "judge_ensemble_summary.csv").exists()
