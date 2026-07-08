from pathlib import Path

import yaml

from legal_eval_harness.product_boundary_dataset import (
    ALLOWED_BOUNDARY_SLICES,
    load_product_boundary_cases,
    validate_product_boundary_cases,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/eval_sets/legal_product_boundary_pilot_v1.jsonl"
CONFIG = ROOT / "config.qianfan_product_boundary_eval.yaml"
RUNNABLE_CONFIG = ROOT / "config.qianfan_product_boundary_runnable.yaml"


def test_product_boundary_dataset_schema_and_slice_counts():
    cases = load_product_boundary_cases(DATASET)
    errors = validate_product_boundary_cases(cases)
    assert errors == []

    case_ids = [case["case_id"] for case in cases]
    assert len(case_ids) == len(set(case_ids))
    assert len(cases) == 50

    slice_counts = {}
    for case in cases:
        slice_counts[case["slice"]] = slice_counts.get(case["slice"], 0) + 1
    assert set(slice_counts) == ALLOWED_BOUNDARY_SLICES
    assert slice_counts == {
        "normal_practice": 10,
        "hard_legal_reasoning": 9,
        "risk_calibration": 8,
        "citation_grounding": 8,
        "adversarial_trap": 7,
        "counterfactual_pair": 8,
    }


def test_product_boundary_counterfactual_pairs_are_complete():
    cases = load_product_boundary_cases(DATASET)
    pairs: dict[str, set[str]] = {}
    for case in cases:
        if case["slice"] == "counterfactual_pair":
            pairs.setdefault(case["pair_id"], set()).add(case["pair_variant"])
            assert case["case_id"].endswith(case["pair_variant"])
            assert case["material_fact_change"]

    assert pairs == {
        "LPB-CF-001": {"A", "B"},
        "LPB-CF-002": {"A", "B"},
        "LPB-CF-003": {"A", "B"},
        "LPB-CF-004": {"A", "B"},
    }


def test_product_boundary_citation_cases_have_context_and_sources():
    cases = load_product_boundary_cases(DATASET)
    citation_cases = [case for case in cases if case["slice"] == "citation_grounding"]
    assert citation_cases
    for case in citation_cases:
        assert case["provided_context"]
        assert case["allowed_sources"]
        context_ids = {item["source_id"] for item in case["provided_context"]}
        assert set(case["allowed_sources"]).issubset(context_ids)


def test_qianfan_product_boundary_config_covers_models_workflows_and_slices():
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    aliases = {model["alias"] for model in config["models"]}
    assert {
        "qianfan_ernie_50",
        "qianfan_deepseek_v4_pro",
        "qianfan_qwen35_27b",
        "qianfan_glm_52",
        "qianfan_kimi_k26",
        "qianfan_lite_baseline",
    }.issubset(aliases)

    workflow_ids = {workflow["id"] for workflow in config["workflow_conditions"]}
    assert workflow_ids == {
        "w0_closed_book",
        "w1_structured_legal_prompt",
        "w2_rag_grounded",
        "w3_rag_verifier_router",
        "w4_clarification_first",
    }

    assert set(config["dataset"]["stratified_slices"]) == ALLOWED_BOUNDARY_SLICES
    assert config["scoring"]["critical_failure_blocks_release"] is True
    assert config["judge"]["mock_compatible"] is True
    assert config["judge_ensemble"]["self_eval_exclusion"] is True
    assert {judge["alias"] for judge in config["judge_ensemble"]["primary_judges"]} == {
        "judge_deepseek_v4_pro",
        "judge_glm_52",
    }
    assert config["judge_ensemble"]["arbiter"]["alias"] == "judge_kimi_k26"
    assert config["rag"]["enabled"] is True
    assert config["rag"]["corpus_path"] == "data/rag_corpus/legal_sources.csv"


def test_qianfan_product_boundary_runnable_config_maps_all_current_workflows():
    config = yaml.safe_load(RUNNABLE_CONFIG.read_text(encoding="utf-8"))
    assert config["run_plan"]["full_versions"] == ["V0", "V1", "V4", "V3", "V5"]
    assert config["workflow_mapping_note"] == {
        "V0": "w0_closed_book",
        "V1": "w1_structured_legal_prompt",
        "V4": "w2_rag_grounded_provided_context",
        "V3": "w3_risk_control_workflow",
        "V5": "w4_clarification_first",
    }
    assert config["judge_ensemble"]["enabled"] is True
    assert config["judge_ensemble"]["self_eval_exclusion"] is True
    assert config["rag"]["retrieval_versions"] == ["V4", "V3"]
