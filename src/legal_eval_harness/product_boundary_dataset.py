from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import DATA_ASSET_ROUTES


ALLOWED_BOUNDARY_SLICES = {
    "normal_practice",
    "hard_legal_reasoning",
    "risk_calibration",
    "citation_grounding",
    "adversarial_trap",
    "counterfactual_pair",
}

ALLOWED_BOUNDARY_DATA_ASSET_ROUTES = set(DATA_ASSET_ROUTES)

ALLOWED_BOUNDARY_RUBRIC_DIMENSIONS = {
    "legal_issue_spotting",
    "material_fact_sensitivity",
    "citation_fidelity",
    "risk_calibration",
    "clarification_behavior",
    "human_review_routing",
    "product_usability",
}

ALLOWED_CRITICAL_FAILURE_LABELS = {
    "fabricated_citation",
    "invented_fact",
    "overconfident_win_rate",
    "unsafe_or_deceptive_assistance",
    "missed_human_review",
    "misclassified_legal_relationship",
    "unsupported_document_claim",
    "ignored_material_fact_change",
    "failed_to_question_bad_premise",
}

REQUIRED_BOUNDARY_FIELDS = {
    "case_id",
    "task_type",
    "slice",
    "jurisdiction",
    "user_prompt",
    "provided_context",
    "expected_behavior",
    "critical_facts",
    "missing_facts",
    "allowed_sources",
    "forbidden_claims",
    "expected_human_review",
    "expected_data_asset_routes",
    "rubric",
    "critical_failure_triggers",
}


def load_product_boundary_cases(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at line {line_no}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"Line {line_no} is not a JSON object")
        rows.append(row)
    return rows


def validate_product_boundary_cases(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    pair_members: dict[str, set[str]] = {}

    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id") or "")
        prefix = f"{case_id or f'line_{index}'}: "
        missing = sorted(REQUIRED_BOUNDARY_FIELDS - set(case))
        if missing:
            errors.append(prefix + f"missing required fields {missing}")
            continue
        if not case_id:
            errors.append(prefix + "case_id is empty")
        elif case_id in seen_ids:
            errors.append(prefix + "duplicate case_id")
        seen_ids.add(case_id)

        slice_name = str(case.get("slice") or "")
        if slice_name not in ALLOWED_BOUNDARY_SLICES:
            errors.append(prefix + f"invalid slice {slice_name!r}")

        if not str(case.get("expected_behavior") or "").strip():
            errors.append(prefix + "expected_behavior is empty")

        routes = case.get("expected_data_asset_routes")
        if not isinstance(routes, list) or not routes:
            errors.append(prefix + "expected_data_asset_routes must be a non-empty list")
        else:
            invalid_routes = sorted(set(map(str, routes)) - ALLOWED_BOUNDARY_DATA_ASSET_ROUTES)
            if invalid_routes:
                errors.append(prefix + f"invalid expected_data_asset_routes values {invalid_routes}")

        rubric = case.get("rubric")
        if not isinstance(rubric, list) or not rubric:
            errors.append(prefix + "rubric must be a non-empty list")
        else:
            for item_index, item in enumerate(rubric, start=1):
                if not isinstance(item, dict):
                    errors.append(prefix + f"rubric item {item_index} is not an object")
                    continue
                dimension = str(item.get("dimension") or "")
                if dimension not in ALLOWED_BOUNDARY_RUBRIC_DIMENSIONS:
                    errors.append(prefix + f"rubric item {item_index} has invalid dimension {dimension!r}")
                if not str(item.get("criterion") or "").strip():
                    errors.append(prefix + f"rubric item {item_index} criterion is empty")
                try:
                    weight = int(item.get("weight", 0))
                except (TypeError, ValueError):
                    weight = 0
                if weight <= 0:
                    errors.append(prefix + f"rubric item {item_index} weight must be positive")

        failures = case.get("critical_failure_triggers")
        if not isinstance(failures, list):
            errors.append(prefix + "critical_failure_triggers must be a list")
        else:
            invalid_failures = sorted(set(map(str, failures)) - ALLOWED_CRITICAL_FAILURE_LABELS)
            if invalid_failures:
                errors.append(prefix + f"invalid critical failure labels {invalid_failures}")

        if slice_name == "citation_grounding":
            context = case.get("provided_context")
            if not isinstance(context, list) or not context:
                errors.append(prefix + "citation_grounding cases must include provided_context")
            allowed_sources = case.get("allowed_sources")
            if not isinstance(allowed_sources, list) or not allowed_sources:
                errors.append(prefix + "citation_grounding cases must include allowed_sources")

        if slice_name == "counterfactual_pair":
            pair_id = str(case.get("pair_id") or "")
            pair_variant = str(case.get("pair_variant") or "")
            material_change = str(case.get("material_fact_change") or "")
            if not pair_id or pair_variant not in {"A", "B"} or not material_change:
                errors.append(prefix + "counterfactual_pair cases need pair_id, pair_variant A/B, and material_fact_change")
            else:
                pair_members.setdefault(pair_id, set()).add(pair_variant)

        if _contains_private_data(case):
            errors.append(prefix + "case appears to contain real private identifiers")

    for pair_id, variants in sorted(pair_members.items()):
        if variants != {"A", "B"}:
            errors.append(f"{pair_id}: counterfactual pair must include both A and B variants")
    return errors


def _contains_private_data(case: dict[str, Any]) -> bool:
    text = json.dumps(case, ensure_ascii=False)
    suspicious_tokens = ["身份证号", "银行卡号", "真实姓名", "手机号：", "手机号码："]
    return any(token in text for token in suspicious_tokens)
