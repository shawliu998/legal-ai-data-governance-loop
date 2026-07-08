from pathlib import Path

from legal_eval_harness.io_excel import find_eval_row, find_gold_row, load_dataset
from legal_eval_harness.prompt_builder import PromptBuilder


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dataset_manifest.yaml"


def test_agent_prompts_do_not_include_gold_label_values():
    bundle = load_dataset(DATA)
    eval_row = find_eval_row(bundle, "L-001")
    gold_row = find_gold_row(bundle, "L-001")
    builder = PromptBuilder(ROOT / "prompts")

    gold_values = [
        gold_row["key_missing_facts"],
        gold_row["expected_answer_points"],
        gold_row["risk_points"],
    ]
    for version in ["V0", "V1", "V2", "V3", "V4", "V5"]:
        prompt, visible = builder.render_agent_prompt(version, eval_row, v0_output="baseline answer")
        assert "key_missing_facts" not in visible
        for value in gold_values:
            assert value not in prompt


def test_judge_prompt_can_include_gold_labels():
    bundle = load_dataset(DATA)
    eval_row = find_eval_row(bundle, "L-001")
    gold_row = find_gold_row(bundle, "L-001")
    builder = PromptBuilder(ROOT / "prompts")

    prompt, prompt_id = builder.render_judge_prompt(
        eval_row=eval_row,
        gold_row=gold_row,
        model_output="test output",
        run_id="RUN-L-001-Model_A-V0",
        version="V0",
    )

    assert prompt_id == "JUDGE_CONSULTATION"
    assert gold_row["key_missing_facts"] in prompt
    assert gold_row["risk_points"] in prompt


def test_judge_prompt_is_task_specific():
    bundle = load_dataset(DATA)
    eval_row = find_eval_row(bundle, "X-DOC-001")
    gold_row = find_gold_row(bundle, "X-DOC-001")
    builder = PromptBuilder(ROOT / "prompts")

    prompt, prompt_id = builder.render_judge_prompt(
        eval_row=eval_row,
        gold_row=gold_row,
        model_output="test output",
        run_id="RUN-X-DOC-001-Model_A-V3",
        version="V3",
    )

    assert prompt_id == "JUDGE_DOCUMENT_DRAFTING"
    assert "Clear and usable structure" in prompt
