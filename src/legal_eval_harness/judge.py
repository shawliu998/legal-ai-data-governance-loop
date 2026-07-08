from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

from .io_excel import DatasetBundle, find_eval_row, find_gold_row
from .llm_client import LLMClient
from .prompt_builder import PromptBuilder
from .schemas import COARSE_ERROR_TAGS, SCORE_DIMENSIONS
from .utils import extract_first_json_object, json_dumps, json_loads_or_none, safe_text


def _risk_level_for_score(score_rate: float, has_high_risk_gold: bool) -> str:
    if score_rate < 0.45 or has_high_risk_gold:
        return "high"
    if score_rate < 0.72:
        return "medium"
    return "low"


def _dimension_scores(version: str, sample_id: str) -> dict[str, int]:
    digest = int(hashlib.sha256(f"{sample_id}-{version}-judge".encode("utf-8")).hexdigest(), 16)
    base_by_version = {"V0": 0, "V1": 1, "V2": 1, "V3": 1, "V4": 1, "V5": 1}
    scores = {}
    for idx, dim in enumerate(SCORE_DIMENSIONS):
        base = base_by_version.get(version, 1)
        if version == "V3" and dim in {"missing_facts_awareness", "risk_coverage", "overclaim_control"}:
            value = 2
        elif version == "V4" and dim in {"legal_grounding", "hallucination_control", "risk_coverage"}:
            value = 2
        elif version == "V5" and dim in {"missing_facts_awareness", "clarification_quality", "overclaim_control"}:
            value = 2
        elif version == "V2" and dim in {"risk_coverage", "overclaim_control", "data_tag_usability"}:
            value = 2
        elif version == "V0" and dim in {"hallucination_control", "legal_grounding"}:
            value = 1
        else:
            value = min(2, base + ((digest >> idx) & 1))
        if version == "V0" and dim in {"clarification_quality", "data_tag_usability"}:
            value = 0
        scores[dim] = int(value)
    return scores


def _subtype_from_gold(gold_row: dict[str, Any]) -> str:
    text = " ".join(
        [
            safe_text(gold_row.get("key_missing_facts")),
            safe_text(gold_row.get("risk_points")),
            safe_text(gold_row.get("expected_answer_points")),
        ]
    )
    keyword_map = [
        ("因果", "missing_causation"),
        ("平台", "platform_liability_unclear"),
        ("贷款", "unsafe_repayment_advice"),
        ("定金", "deposit_term_confusion"),
        ("素材", "missing_ip_risk"),
        ("劳动", "employment_status_unclear"),
        ("证据", "evidence_chain_unclear"),
        ("管辖", "jurisdiction_unclear"),
    ]
    for keyword, subtype in keyword_map:
        if keyword in text:
            return subtype
    return "general_legal_risk"


def _mock_judge_payload(run_row: dict[str, Any], gold_row: dict[str, Any]) -> dict[str, Any]:
    version = safe_text(run_row["version"])
    sample_id = safe_text(run_row["sample_id"])
    task_category = safe_text(run_row.get("task_category", gold_row.get("task_category", "consultation")))
    dimension_scores = _dimension_scores(version, sample_id)
    if task_category == "case_analysis":
        dimension_scores["fact_rule_application"] = min(2, dimension_scores["fact_rule_application"] + 1)
        dimension_scores["legal_grounding"] = min(2, dimension_scores["legal_grounding"] + (1 if version == "V3" else 0))
    elif task_category == "document_drafting":
        dimension_scores["data_tag_usability"] = min(2, dimension_scores["data_tag_usability"] + 1)
        dimension_scores["risk_coverage"] = min(2, dimension_scores["risk_coverage"] + (1 if version in {"V2", "V3"} else 0))
    else:
        dimension_scores["clarification_quality"] = min(2, dimension_scores["clarification_quality"] + (1 if version != "V0" else 0))
    rubric_items = json_loads_or_none(gold_row.get("rubric_items")) or []

    atomic_scores = []
    for idx, item in enumerate(rubric_items):
        if version == "V0":
            score = 0 if idx % 2 == 0 else 1
        elif version == "V1":
            score = 1
        elif version == "V2":
            score = 2 if item.get("criticality") == "high" and idx % 2 else 1
        elif version in {"V4", "V5"}:
            score = 2 if item.get("criticality") == "high" or idx % 2 else 1
        else:
            score = 2 if idx % 3 else 1
        atomic_scores.append(
            {
                "rubric_id": item.get("rubric_id", f"{sample_id}-R{idx+1:02d}"),
                "atomic_rubric_item": item.get("atomic_rubric_item", ""),
                "score": int(score),
                "max_score": int(item.get("max_score") or 2),
                "rationale": "mock judge: deterministic rubric coverage estimate",
            }
        )

    total_score = sum(dimension_scores.values()) + sum(item["score"] for item in atomic_scores)
    max_score = len(SCORE_DIMENSIONS) * 2 + sum(item["max_score"] for item in atomic_scores)
    score_rate = round(total_score / max_score, 3) if max_score else 0.0
    has_high_risk_gold = "高风险" in safe_text(gold_row.get("human_review_note")) or "刑" in safe_text(
        gold_row.get("risk_points")
    )
    risk_level = _risk_level_for_score(score_rate, has_high_risk_gold)

    tags = []
    subtype = _subtype_from_gold(gold_row)
    if version == "V0":
        tags.extend(
            [
                {"coarse_error_tag": "missing_facts", "error_subtype": subtype},
                {"coarse_error_tag": "overclaim", "error_subtype": "premature_conclusion"},
            ]
        )
    elif version == "V1":
        tags.append({"coarse_error_tag": "missing_evidence_warning", "error_subtype": subtype})
        if int(hashlib.sha256(sample_id.encode("utf-8")).hexdigest(), 16) % 2 == 0:
            tags.append({"coarse_error_tag": "overclaim", "error_subtype": "structure_without_sufficient_caution"})
    elif version == "V2":
        tags.append({"coarse_error_tag": "weak_fact_rule_application", "error_subtype": subtype})
    elif version == "V4":
        tags.append({"coarse_error_tag": "unverified_basis", "error_subtype": "grounding_boundary_check"})
    elif version == "V5":
        tags.append({"coarse_error_tag": "missing_facts", "error_subtype": "clarification_first"})
    else:
        tags.append({"coarse_error_tag": "missing_evidence_warning", "error_subtype": subtype})
    if risk_level == "high":
        tags.append({"coarse_error_tag": "needs_human_review", "error_subtype": "high_risk_or_low_score"})

    return {
        "dimension_scores": dimension_scores,
        "atomic_scores": atomic_scores,
        "total_score": total_score,
        "max_score": max_score,
        "score_rate": score_rate,
        "error_tags": tags,
        "risk_level": risk_level,
        "judge_reason": (
            f"mock {task_category} judge based on gold labels, rubric items, and observed output shape; "
            "not legal correctness."
        ),
        "judge_confidence": "medium" if risk_level != "high" else "low",
        "needs_human_review": risk_level == "high" or any(t["coarse_error_tag"] == "needs_human_review" for t in tags),
    }


def normalize_judge_payload(payload: dict[str, Any]) -> dict[str, Any]:
    dimension_scores_raw = payload.get("dimension_scores") or {}
    dimension_scores: dict[str, int] = {}
    for dim in SCORE_DIMENSIONS:
        try:
            score = int(dimension_scores_raw.get(dim, 0))
        except (TypeError, ValueError):
            score = 0
        dimension_scores[dim] = max(0, min(2, score))

    atomic_scores = []
    for item in payload.get("atomic_scores") or []:
        if not isinstance(item, dict):
            continue
        try:
            max_score = int(item.get("max_score", 2))
        except (TypeError, ValueError):
            max_score = 2
        max_score = max(1, min(2, max_score))
        try:
            score = int(item.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        atomic_scores.append(
            {
                "rubric_id": safe_text(item.get("rubric_id")),
                "atomic_rubric_item": safe_text(item.get("atomic_rubric_item")),
                "score": max(0, min(max_score, score)),
                "max_score": max_score,
                "rationale": safe_text(item.get("rationale")),
            }
        )

    total_score = sum(dimension_scores.values()) + sum(item["score"] for item in atomic_scores)
    max_score = len(SCORE_DIMENSIONS) * 2 + sum(item["max_score"] for item in atomic_scores)
    score_rate = round(total_score / max_score, 3) if max_score else 0.0

    tags = payload.get("error_tags") or []
    normalized_tags = []
    for tag in tags:
        if not isinstance(tag, dict):
            continue
        coarse = safe_text(tag.get("coarse_error_tag"))
        subtype = safe_text(tag.get("error_subtype"))
        if coarse not in COARSE_ERROR_TAGS:
            coarse = "needs_human_review"
            subtype = subtype or "non_standard_error_tag"
        normalized_tags.append({"coarse_error_tag": coarse, "error_subtype": subtype})

    risk_level = safe_text(payload.get("risk_level")).lower()
    if risk_level not in {"low", "medium", "high"}:
        risk_level = "high" if score_rate < 0.45 else "medium" if score_rate < 0.72 else "low"
    judge_confidence = safe_text(payload.get("judge_confidence")).lower()
    if judge_confidence not in {"low", "medium", "high"}:
        judge_confidence = "medium"
    needs_human_review = payload.get("needs_human_review")
    if isinstance(needs_human_review, str):
        needs_human_review = needs_human_review.strip().lower() in {"true", "yes", "1", "是"}

    return {
        "dimension_scores": dimension_scores,
        "atomic_scores": atomic_scores,
        "total_score": total_score,
        "max_score": max_score,
        "score_rate": score_rate,
        "error_tags": normalized_tags,
        "risk_level": risk_level,
        "judge_reason": safe_text(payload.get("judge_reason")),
        "judge_confidence": judge_confidence,
        "needs_human_review": bool(needs_human_review),
    }


def _api_judge_payload(
    *,
    prompt: str,
    judge_config: dict[str, Any],
    config: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    client = LLMClient(config, mode="api")
    try:
        text = client.generate(prompt=prompt, model_config=judge_config, version="JUDGE", sample_id="judge")
    except Exception as exc:
        return None, f"API_ERROR: {type(exc).__name__}: {safe_text(exc)}"
    try:
        return extract_first_json_object(text), text
    except Exception:
        return None, text


def run_judge(
    *,
    runs: pd.DataFrame,
    bundle: DatasetBundle,
    config: dict[str, Any],
    mode: str,
    output_path: str | Path,
    prompt_dir: str | Path = "prompts",
) -> pd.DataFrame:
    builder = PromptBuilder(prompt_dir)
    rows: list[dict[str, Any]] = []
    judge_config = config.get("judge") or {}

    for _, run in tqdm(runs.iterrows(), total=len(runs), desc="judge"):
        run_row = run.to_dict()
        sample_id = safe_text(run_row["sample_id"])
        gold_row = find_gold_row(bundle, sample_id)
        eval_row = find_eval_row(bundle, sample_id)
        parsed_ok = True
        raw_judge_output = ""
        if run_row.get("run_status") != "ok":
            payload = {
                "dimension_scores": {dim: 0 for dim in SCORE_DIMENSIONS},
                "atomic_scores": [],
                "total_score": 0,
                "max_score": len(SCORE_DIMENSIONS) * 2,
                "score_rate": 0.0,
                "error_tags": [{"coarse_error_tag": "needs_human_review", "error_subtype": "model_run_failed"}],
                "risk_level": "high",
                "judge_reason": "model run failed before judging",
                "judge_confidence": "low",
                "needs_human_review": True,
            }
        elif mode == "mock":
            payload = _mock_judge_payload(run_row, gold_row)
        else:
            prompt, judge_prompt_id = builder.render_judge_prompt(
                eval_row=eval_row,
                gold_row=gold_row,
                model_output=safe_text(run_row.get("output_text", "")),
                run_id=safe_text(run_row["run_id"]),
                version=safe_text(run_row["version"]),
            )
            payload, raw_judge_output = _api_judge_payload(prompt=prompt, judge_config=judge_config, config=config)
            if payload is None:
                parsed_ok = False
                payload = {
                    "dimension_scores": {dim: 0 for dim in SCORE_DIMENSIONS},
                    "atomic_scores": [],
                    "total_score": 0,
                    "max_score": len(SCORE_DIMENSIONS) * 2,
                    "score_rate": 0.0,
                    "error_tags": [
                        {"coarse_error_tag": "needs_human_review", "error_subtype": "judge_parse_failed"}
                    ],
                    "risk_level": "high",
                    "judge_reason": "judge output parse failed",
                    "judge_confidence": "low",
                    "needs_human_review": True,
                }
        if mode == "mock" or run_row.get("run_status") != "ok":
            task_category = safe_text(eval_row.get("task_category", "consultation")) or "consultation"
            judge_prompt_id = {
                "consultation": "JUDGE_CONSULTATION",
                "case_analysis": "JUDGE_CASE_ANALYSIS",
                "document_drafting": "JUDGE_DOCUMENT_DRAFTING",
            }.get(task_category, "JUDGE_CONSULTATION")

        for tag in payload.get("error_tags", []):
            if tag.get("coarse_error_tag") not in COARSE_ERROR_TAGS:
                tag["coarse_error_tag"] = "needs_human_review"
                tag["error_subtype"] = tag.get("error_subtype") or "non_standard_error_tag"
        payload = normalize_judge_payload(payload)

        rows.append(
            {
                "run_id": run_row["run_id"],
                "sample_id": sample_id,
                "source_dataset": eval_row.get("source_dataset", run_row.get("source_dataset", "")),
                "task_category": eval_row.get("task_category", run_row.get("task_category", "")),
                "model_alias": run_row["model_alias"],
                "version": run_row["version"],
                "judge_prompt_id": judge_prompt_id,
                "dimension_scores": json_dumps(payload["dimension_scores"]),
                "atomic_scores": json_dumps(payload["atomic_scores"]),
                "total_score": int(payload["total_score"]),
                "max_score": int(payload["max_score"]),
                "score_rate": round(float(payload["score_rate"]), 3),
                "error_tags": json_dumps(payload["error_tags"]),
                "risk_level": payload["risk_level"],
                "judge_reason": payload["judge_reason"],
                "judge_confidence": payload["judge_confidence"],
                "needs_human_review": bool(payload["needs_human_review"]),
                "parsed_ok": bool(parsed_ok),
                "raw_judge_output": raw_judge_output,
            }
        )

    df = pd.DataFrame(rows)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return df
