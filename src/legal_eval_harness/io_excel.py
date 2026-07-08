from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .schemas import GOLD_LABEL_FIELDS, PROTECTED_GOLD_FIELDS, TASK_CATEGORIES, VISIBLE_INPUT_FIELDS
from .utils import json_dumps, json_loads_or_none, safe_text


@dataclass(frozen=True)
class DatasetBundle:
    eval_input: pd.DataFrame
    gold_labels: pd.DataFrame
    rubric_items: pd.DataFrame
    sample_index: pd.DataFrame
    source_routing: pd.DataFrame
    manifest: dict[str, Any] | None = None


def _read_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, sheet_name=sheet_name)
    except ValueError as exc:
        raise ValueError(f"Missing required sheet: {sheet_name}") from exc
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    if "sample_id" in df.columns:
        df["sample_id"] = df["sample_id"].map(safe_text)
    return df


def _normalize_frame_strings(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for col in normalized.columns:
        if normalized[col].dtype == object:
            normalized[col] = normalized[col].map(safe_text)
    if "sample_id" in normalized.columns:
        normalized["sample_id"] = normalized["sample_id"].map(safe_text)
    return normalized


def _infer_task_category(task_type: str, legal_domain: str = "") -> str:
    text = f"{task_type} {legal_domain}".lower()
    if "draft" in text or "rewrite" in text or "文书" in text or "起诉状" in text or "函" in text:
        return "document_drafting"
    if "analysis" in text or "claim verification" in text or "case" in text or "案例" in text:
        return "case_analysis"
    return "consultation"


def _validate_eval_visibility(eval_input: pd.DataFrame) -> None:
    leaked = sorted(PROTECTED_GOLD_FIELDS.intersection(eval_input.columns))
    if leaked:
        raise AssertionError(f"Eval_Input contains protected gold fields: {leaked}")
    missing = [field for field in VISIBLE_INPUT_FIELDS if field not in eval_input.columns]
    if missing:
        raise ValueError(f"Eval_Input missing required visible fields: {missing}")
    invalid_categories = sorted(set(eval_input["task_category"]) - set(TASK_CATEGORIES))
    if invalid_categories:
        raise ValueError(f"Eval_Input contains invalid task_category values: {invalid_categories}")


def _load_normalized_dataset(manifest_path: Path) -> DatasetBundle:
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh) or {}
    root = manifest_path.parent
    files = manifest.get("files") or {}
    eval_path = root / files.get("eval_input", "eval_input.csv")
    gold_path = root / files.get("gold_labels", "gold_labels.csv")
    rubric_path = root / files.get("rubric_items", "rubric_items.csv")
    for path in [eval_path, gold_path, rubric_path]:
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")

    eval_input = _normalize_frame_strings(pd.read_csv(eval_path))
    gold_labels = _normalize_frame_strings(pd.read_csv(gold_path))
    rubric_items = _normalize_frame_strings(pd.read_csv(rubric_path))

    if "rubric_items" not in gold_labels.columns:
        grouped: dict[str, list[dict[str, Any]]] = {}
        wanted = [
            "rubric_id",
            "rubric_dimension",
            "atomic_rubric_item",
            "max_score",
            "scoring_rule_2",
            "scoring_rule_1",
            "scoring_rule_0",
            "criticality",
            "negative_rule",
        ]
        for col in wanted:
            if col not in rubric_items.columns:
                rubric_items[col] = ""
        for sample_id, rows in rubric_items.groupby("sample_id"):
            records: list[dict[str, Any]] = []
            for record in rows[wanted].to_dict(orient="records"):
                normalized = {key: safe_text(value) for key, value in record.items()}
                normalized["max_score"] = int(float(normalized["max_score"] or 2))
                records.append(normalized)
            grouped[sample_id] = records
        gold_labels["rubric_items"] = gold_labels["sample_id"].map(lambda sid: json_dumps(grouped.get(sid, [])))
    else:
        gold_labels["rubric_items"] = gold_labels["rubric_items"].map(
            lambda value: json_dumps(json_loads_or_none(value) or [])
        )

    _validate_eval_visibility(eval_input)
    eval_input = eval_input[VISIBLE_INPUT_FIELDS]
    gold_labels = gold_labels[GOLD_LABEL_FIELDS]
    sample_index = eval_input[
        ["sample_id", "source_dataset", "task_category", "task_type", "jurisdiction"]
    ].copy()
    source_routing = pd.DataFrame(columns=["sample_id"])
    return DatasetBundle(
        eval_input=eval_input,
        gold_labels=gold_labels,
        rubric_items=rubric_items,
        sample_index=sample_index,
        source_routing=source_routing,
        manifest=manifest,
    )


def _records_for_rubric(rubric_items: pd.DataFrame, sample_id: str) -> list[dict[str, Any]]:
    rows = rubric_items[rubric_items["sample_id"] == sample_id].copy()
    wanted = [
        "rubric_id",
        "rubric_dimension",
        "atomic_rubric_item",
        "max_score",
        "scoring_rule_2",
        "scoring_rule_1",
        "scoring_rule_0",
        "criticality",
        "negative_rule",
    ]
    for col in wanted:
        if col not in rows.columns:
            rows[col] = ""
    records: list[dict[str, Any]] = []
    for record in rows[wanted].to_dict(orient="records"):
        normalized = {key: safe_text(value) for key, value in record.items()}
        normalized["max_score"] = int(float(normalized["max_score"] or 2))
        records.append(normalized)
    return records


def load_dataset(
    input_path: str | Path,
    jurisdiction: str = "中国大陆",
    law_snapshot_date: str = "2026-07-07",
    legal_advice_boundary: str = "仅用于诊断评测，不构成法律咨询或最终法律意见。",
) -> DatasetBundle:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input workbook not found: {path}")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return _load_normalized_dataset(path)

    task_set = _read_sheet(path, "Task_Set")
    sample_index = _read_sheet(path, "Sample_Index")
    rubric_items = _read_sheet(path, "Rubric_Items")
    try:
        source_routing = _read_sheet(path, "Error_Tags_Data_Routing")
    except ValueError:
        source_routing = pd.DataFrame(columns=["sample_id"])

    required_task = [
        "sample_id",
        "user_question",
        "known_facts",
        "legal_concepts",
        "key_missing_facts",
        "expected_clarification_questions",
        "expected_answer_points",
        "risk_points",
        "expected_behavior",
    ]
    missing = [col for col in required_task if col not in task_set.columns]
    if missing:
        raise ValueError(f"Task_Set missing required columns: {missing}")

    meta_cols = [col for col in ["sample_id", "task_type", "legal_domain"] if col in sample_index.columns]
    task_type = sample_index[meta_cols].copy() if meta_cols else None
    if task_type is not None:
        task_set = task_set.merge(task_type, on="sample_id", how="left")
    else:
        task_set["task_type"] = ""
        task_set["legal_domain"] = ""

    eval_input = pd.DataFrame(
        {
            "sample_id": task_set["sample_id"].map(safe_text),
            "source_dataset": "self_authored_core",
            "task_category": [
                _infer_task_category(safe_text(row.get("task_type", "")), safe_text(row.get("legal_domain", "")))
                for _, row in task_set.iterrows()
            ],
            "user_question": task_set["user_question"].map(safe_text),
            "known_facts": task_set["known_facts"].map(safe_text),
            "legal_concepts": task_set["legal_concepts"].map(safe_text),
            "jurisdiction": jurisdiction,
            "law_snapshot_date": law_snapshot_date,
            "task_type": task_set["task_type"].map(safe_text),
            "legal_advice_boundary": legal_advice_boundary,
        }
    )

    gold_records = []
    routing_notes = {}
    if not source_routing.empty and "route_reason" in source_routing.columns:
        routing_notes = dict(zip(source_routing["sample_id"], source_routing["route_reason"]))
    for _, row in task_set.iterrows():
        sample_id = safe_text(row["sample_id"])
        human_review_note = safe_text(routing_notes.get(sample_id, ""))
        gold_records.append(
            {
                "sample_id": sample_id,
                "source_dataset": "self_authored_core",
                "task_category": _infer_task_category(
                    safe_text(row.get("task_type", "")), safe_text(row.get("legal_domain", ""))
                ),
                "key_missing_facts": safe_text(row["key_missing_facts"]),
                "expected_clarification_questions": safe_text(row["expected_clarification_questions"]),
                "expected_answer_points": safe_text(row["expected_answer_points"]),
                "risk_points": safe_text(row["risk_points"]),
                "expected_behavior": safe_text(row["expected_behavior"]),
                "rubric_items": json_dumps(_records_for_rubric(rubric_items, sample_id)),
                "human_review_note": human_review_note,
            }
        )
    gold_labels = pd.DataFrame(gold_records, columns=GOLD_LABEL_FIELDS)

    _validate_eval_visibility(eval_input)
    eval_input = eval_input[VISIBLE_INPUT_FIELDS]
    return DatasetBundle(
        eval_input=eval_input,
        gold_labels=gold_labels,
        rubric_items=rubric_items,
        sample_index=sample_index,
        source_routing=source_routing,
    )


def find_eval_row(bundle: DatasetBundle, sample_id: str) -> dict[str, Any]:
    rows = bundle.eval_input[bundle.eval_input["sample_id"] == sample_id]
    if rows.empty:
        raise KeyError(f"Unknown sample_id: {sample_id}")
    return rows.iloc[0].to_dict()


def find_gold_row(bundle: DatasetBundle, sample_id: str) -> dict[str, Any]:
    rows = bundle.gold_labels[bundle.gold_labels["sample_id"] == sample_id]
    if rows.empty:
        raise KeyError(f"Unknown sample_id: {sample_id}")
    return rows.iloc[0].to_dict()
