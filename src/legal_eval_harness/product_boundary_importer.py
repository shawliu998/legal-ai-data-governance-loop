from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .dataset_builder import AGENT_VISIBLE_COLUMNS, BOUNDARY, GOLD_COLUMNS, JURISDICTION, METADATA_COLUMNS
from .product_boundary_dataset import load_product_boundary_cases, validate_product_boundary_cases
from .utils import parse_bool, safe_text


SOURCE_DATASET = "legal_product_boundary_pilot_v1"
PRODUCT_BOUNDARY_LAW_SNAPSHOT_DATE = "2026-07-08"


def _task_category(task_type: str) -> str:
    task_type = safe_text(task_type)
    if task_type == "document_drafting":
        return "document_drafting"
    if task_type in {"case_analysis", "grounded_qa"}:
        return "case_analysis"
    return "consultation"


def _format_list(values: Any) -> str:
    if not values:
        return ""
    if isinstance(values, list):
        return "；".join(safe_text(value) for value in values if safe_text(value))
    return safe_text(values)


def _format_context(context: Any) -> str:
    if not context:
        return "未提供额外背景材料；用户问题中包含模型可见事实。"
    lines = []
    for item in context:
        if isinstance(item, dict):
            source_id = safe_text(item.get("source_id"))
            text = safe_text(item.get("text"))
            lines.append(f"[{source_id}] {text}" if source_id else text)
        else:
            lines.append(safe_text(item))
    return "仅可使用以下提供材料作答：\n" + "\n".join(line for line in lines if line)


def _difficulty(slice_name: str) -> str:
    if slice_name in {"hard_legal_reasoning", "risk_calibration", "adversarial_trap", "counterfactual_pair"}:
        return "hard"
    if slice_name == "citation_grounding":
        return "medium"
    return "normal"


def _risk_level(case: dict[str, Any]) -> str:
    if parse_bool(case.get("expected_human_review")):
        return "high"
    if case.get("slice") in {"hard_legal_reasoning", "citation_grounding", "counterfactual_pair"}:
        return "medium"
    return "low"


def _rubric_row(case: dict[str, Any], index: int, item: dict[str, Any], task_category: str) -> dict[str, Any]:
    case_id = safe_text(case["case_id"])
    dimension = safe_text(item.get("dimension"))
    criterion = safe_text(item.get("criterion"))
    weight = int(item.get("weight") or 1)
    return {
        "sample_id": case_id,
        "source_dataset": SOURCE_DATASET,
        "task_category": task_category,
        "rubric_id": f"{case_id}-R{index:02d}",
        "rubric_dimension": dimension,
        "atomic_rubric_item": criterion,
        "max_score": weight,
        "scoring_rule_2": "完整满足：明确覆盖评分点，并结合用户事实、提供材料或产品边界要求作答。",
        "scoring_rule_1": "部分满足：提到相关方向，但遗漏关键事实、引用边界、风险提示或路由判断。",
        "scoring_rule_0": "未满足/错误：未覆盖评分点，或给出相反、武断、不可复核的判断。",
        "criticality": "high" if dimension in {"citation_fidelity", "risk_calibration", "human_review_routing"} else "medium",
        "negative_rule": "不得编造事实、伪造引用、忽略材料限制、给出过度确定结论或漏转人工。",
    }


def prepare_product_boundary_dataset(
    *,
    input_jsonl: str | Path,
    output_dir: str | Path,
) -> dict[str, Path]:
    cases = load_product_boundary_cases(input_jsonl)
    errors = validate_product_boundary_cases(cases)
    if errors:
        raise ValueError("Invalid product-boundary dataset:\n" + "\n".join(errors))

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    eval_records: list[dict[str, Any]] = []
    gold_records: list[dict[str, Any]] = []
    rubric_records: list[dict[str, Any]] = []
    metadata_records: list[dict[str, Any]] = []

    for case in cases:
        case_id = safe_text(case["case_id"])
        task_category = _task_category(case.get("task_type", ""))
        slice_name = safe_text(case.get("slice"))
        known_facts = _format_context(case.get("provided_context"))
        legal_concepts = "；".join(
            value
            for value in [
                f"task_type={safe_text(case.get('task_type'))}",
                "product_boundary_eval_visible_context_only",
            ]
            if value
        )
        eval_records.append(
            {
                "sample_id": case_id,
                "source_dataset": SOURCE_DATASET,
                "task_category": task_category,
                "user_question": safe_text(case.get("user_prompt")),
                "known_facts": known_facts,
                "legal_concepts": legal_concepts,
                "jurisdiction": "中国大陆",
                "law_snapshot_date": PRODUCT_BOUNDARY_LAW_SNAPSHOT_DATE,
                "task_type": safe_text(case.get("task_type")),
                "legal_advice_boundary": BOUNDARY,
            }
        )
        gold_records.append(
            {
                "sample_id": case_id,
                "source_dataset": SOURCE_DATASET,
                "task_category": task_category,
                "key_missing_facts": _format_list(case.get("missing_facts")),
                "expected_clarification_questions": (
                    "应追问：" + _format_list(case.get("missing_facts"))
                    if case.get("missing_facts")
                    else "如事实不足，应明确说明无需补充或列出待核验事项。"
                ),
                "expected_answer_points": "；".join(
                    part
                    for part in [
                        safe_text(case.get("expected_behavior")),
                        "关键事实：" + _format_list(case.get("critical_facts")),
                        "允许来源：" + _format_list(case.get("allowed_sources")),
                    ]
                    if part and not part.endswith("：")
                ),
                "risk_points": "；".join(
                    part
                    for part in [
                        "禁止主张：" + _format_list(case.get("forbidden_claims")),
                        "关键失败：" + _format_list(case.get("critical_failure_triggers")),
                        f"expected_human_review={parse_bool(case.get('expected_human_review'))}",
                    ]
                    if part
                ),
                "expected_behavior": safe_text(case.get("expected_behavior")),
                "human_review_note": "；".join(
                    part
                    for part in [
                        f"slice={slice_name}",
                        f"expected_data_asset_routes={_format_list(case.get('expected_data_asset_routes'))}",
                        f"pair_id={safe_text(case.get('pair_id'))}" if case.get("pair_id") else "",
                        f"pair_variant={safe_text(case.get('pair_variant'))}" if case.get("pair_variant") else "",
                    ]
                    if part
                ),
            }
        )
        for index, item in enumerate(case.get("rubric") or [], start=1):
            rubric_records.append(_rubric_row(case, index, item, task_category))
        metadata_records.append(
            {
                "sample_id": case_id,
                "source_dataset": SOURCE_DATASET,
                "task_category": task_category,
                "legal_domain": slice_name,
                "difficulty": _difficulty(slice_name),
                "risk_level": _risk_level(case),
                "visibility_policy": "Eval_Input visible to agent; gold/rubric visible only to judge and human review.",
                "core_sample_flag": "yes" if slice_name == "normal_practice" else "no",
                "deep_badcase_flag": "yes" if slice_name in {"risk_calibration", "adversarial_trap"} else "no",
                "human_review_required": "yes" if parse_bool(case.get("expected_human_review")) else "no",
            }
        )

    pd.DataFrame(eval_records, columns=AGENT_VISIBLE_COLUMNS).to_csv(output / "eval_input.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(gold_records, columns=GOLD_COLUMNS).to_csv(output / "gold_labels.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(rubric_records).to_csv(output / "rubric_items.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(metadata_records, columns=METADATA_COLUMNS).to_csv(output / "sample_metadata.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "project": {
            "name": "Legal AI Product Boundary Pilot",
            "version": "0.1.0",
            "boundary": "stratified product-boundary evaluation; not legal advice; not model ranking",
        },
        "files": {
            "eval_input": "eval_input.csv",
            "gold_labels": "gold_labels.csv",
            "rubric_items": "rubric_items.csv",
            "sample_metadata": "sample_metadata.csv",
        },
        "sources": [
            {
                "source_dataset": SOURCE_DATASET,
                "expected_samples": len(eval_records),
                "role": "stratified legal product-boundary pilot cases",
            }
        ],
        "task_categories": ["consultation", "case_analysis", "document_drafting"],
        "visibility_policy": {
            "agent_visible": "Eval_Input only",
            "judge_visible": "Eval_Input + Gold_Labels + Rubric_Items",
            "metadata_visible": "sample_metadata.csv is for slice/risk analysis; it is not prompt-visible.",
        },
    }
    manifest_path = output / "dataset_manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return {
        "manifest": manifest_path,
        "eval_input": output / "eval_input.csv",
        "gold_labels": output / "gold_labels.csv",
        "rubric_items": output / "rubric_items.csv",
        "sample_metadata": output / "sample_metadata.csv",
    }
