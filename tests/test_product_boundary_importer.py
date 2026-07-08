from pathlib import Path

from legal_eval_harness.io_excel import load_dataset
from legal_eval_harness.product_boundary_importer import prepare_product_boundary_dataset
from legal_eval_harness.runner import build_run_plan


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/eval_sets/legal_product_boundary_pilot_v1.jsonl"


def test_prepare_product_boundary_dataset_outputs_loadable_manifest(tmp_path):
    paths = prepare_product_boundary_dataset(input_jsonl=DATASET, output_dir=tmp_path / "product_boundary")
    bundle = load_dataset(paths["manifest"])

    assert len(bundle.eval_input) == 50
    assert len(bundle.gold_labels) == 50
    assert len(bundle.rubric_items) == 200
    assert set(bundle.eval_input["task_category"]) == {"consultation", "case_analysis", "document_drafting"}

    config = {
        "models": [
            {"alias": "Model_A", "provider": "mock", "model": "mock"},
            {"alias": "Model_B", "provider": "mock", "model": "mock"},
        ],
        "run_plan": {"full_samples": "all", "full_versions": ["V0", "V1", "V3"], "deep_samples": []},
    }
    assert len(build_run_plan(bundle, config)) == 300
