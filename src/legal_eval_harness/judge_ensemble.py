from __future__ import annotations

from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd
from tqdm import tqdm

from .io_excel import DatasetBundle, find_eval_row, find_gold_row
from .judge import _api_judge_payload, _mock_judge_payload, normalize_judge_payload
from .prompt_builder import PromptBuilder
from .router import route_one
from .schemas import COARSE_ERROR_TAGS, SCORE_DIMENSIONS
from .utils import json_dumps, json_loads_or_none, safe_text


CRITICAL_COARSE_TAGS = {
    "fabricated_citation",
    "unsafe_action_suggestion",
    "needs_human_review",
    "unverified_basis",
}
RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def _normal(value: Any) -> str:
    return safe_text(value).lower().replace(" ", "").replace("-", "").replace("_", "")


def _judge_alias(judge_config: dict[str, Any], index: int = 0) -> str:
    return (
        safe_text(judge_config.get("alias"))
        or safe_text(judge_config.get("model"))
        or f"judge_{index + 1}"
    )


def _matches_answer_model(judge_config: dict[str, Any], run_row: dict[str, Any]) -> bool:
    judge_values = {
        _normal(judge_config.get("alias")),
        _normal(judge_config.get("vendor")),
        _normal(judge_config.get("family")),
        _normal(judge_config.get("model")),
    }
    answer_values = {
        _normal(run_row.get("model_alias")),
        _normal(run_row.get("model_vendor")),
        _normal(run_row.get("model_family")),
        _normal(run_row.get("model_name")),
    }
    judge_values.discard("")
    answer_values.discard("")
    return bool(judge_values.intersection(answer_values))


def _failed_judge_payload() -> dict[str, Any]:
    return {
        "dimension_scores": {dim: 0 for dim in SCORE_DIMENSIONS},
        "atomic_scores": [],
        "total_score": 0,
        "max_score": len(SCORE_DIMENSIONS) * 2,
        "score_rate": 0.0,
        "error_tags": [{"coarse_error_tag": "needs_human_review", "error_subtype": "model_run_failed"}],
        "risk_level": "high",
        "judge_reason": "model run failed before ensemble judging",
        "judge_confidence": "low",
        "needs_human_review": True,
    }


def _parse_error_tags(value: Any) -> list[dict[str, str]]:
    parsed = json_loads_or_none(value) or []
    tags: list[dict[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        coarse = safe_text(item.get("coarse_error_tag"))
        subtype = safe_text(item.get("error_subtype"))
        if coarse not in COARSE_ERROR_TAGS:
            coarse = "needs_human_review"
            subtype = subtype or "non_standard_error_tag"
        tags.append({"coarse_error_tag": coarse, "error_subtype": subtype})
    return tags


def _critical_tag_set(score_row: dict[str, Any]) -> set[str]:
    return {
        tag["coarse_error_tag"]
        for tag in _parse_error_tags(score_row.get("error_tags"))
        if tag["coarse_error_tag"] in CRITICAL_COARSE_TAGS
    }


def _max_risk(values: list[str]) -> str:
    return max(values or ["medium"], key=lambda value: RISK_ORDER.get(safe_text(value), 1))


def _most_common(values: list[str], default: str = "") -> str:
    if not values:
        return default
    return Counter(values).most_common(1)[0][0]


def _judge_payload_for_run(
    *,
    run_row: dict[str, Any],
    gold_row: dict[str, Any],
    eval_row: dict[str, Any],
    judge_config: dict[str, Any],
    config: dict[str, Any],
    mode: str,
    builder: PromptBuilder,
) -> tuple[dict[str, Any], bool, str, str]:
    raw_judge_output = ""
    parsed_ok = True
    task_category = safe_text(eval_row.get("task_category", "consultation")) or "consultation"
    judge_prompt_id = {
        "consultation": "JUDGE_CONSULTATION",
        "case_analysis": "JUDGE_CASE_ANALYSIS",
        "document_drafting": "JUDGE_DOCUMENT_DRAFTING",
    }.get(task_category, "JUDGE_CONSULTATION")

    if run_row.get("run_status") != "ok":
        return _failed_judge_payload(), parsed_ok, raw_judge_output, judge_prompt_id
    if mode == "mock":
        return _mock_judge_payload(run_row, gold_row), parsed_ok, raw_judge_output, judge_prompt_id

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
            "error_tags": [{"coarse_error_tag": "needs_human_review", "error_subtype": "judge_parse_failed"}],
            "risk_level": "high",
            "judge_reason": "judge output parse failed",
            "judge_confidence": "low",
            "needs_human_review": True,
        }
    return payload, parsed_ok, raw_judge_output, judge_prompt_id


def _score_row(
    *,
    run_row: dict[str, Any],
    eval_row: dict[str, Any],
    payload: dict[str, Any],
    parsed_ok: bool,
    raw_judge_output: str,
    judge_prompt_id: str,
    judge_config: dict[str, Any],
    judge_role: str,
    blocked_aliases: list[str],
) -> dict[str, Any]:
    tags = payload.get("error_tags", [])
    for tag in tags:
        if tag.get("coarse_error_tag") not in COARSE_ERROR_TAGS:
            tag["coarse_error_tag"] = "needs_human_review"
            tag["error_subtype"] = tag.get("error_subtype") or "non_standard_error_tag"
    payload = normalize_judge_payload(payload)
    tags = payload.get("error_tags", [])
    judge_alias = _judge_alias(judge_config)
    return {
        "run_id": run_row["run_id"],
        "sample_id": safe_text(run_row["sample_id"]),
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
        "error_tags": json_dumps(tags),
        "risk_level": payload["risk_level"],
        "judge_reason": payload["judge_reason"],
        "judge_confidence": payload["judge_confidence"],
        "needs_human_review": bool(payload["needs_human_review"]),
        "parsed_ok": bool(parsed_ok),
        "raw_judge_output": raw_judge_output,
        "answer_model_alias": safe_text(run_row.get("model_alias")),
        "answer_model_vendor": safe_text(run_row.get("model_vendor")),
        "answer_model_family": safe_text(run_row.get("model_family")),
        "judge_model_alias": judge_alias,
        "judge_vendor": safe_text(judge_config.get("vendor")),
        "judge_family": safe_text(judge_config.get("family")),
        "judge_role": judge_role,
        "self_eval_exclusion_enabled": bool(blocked_aliases),
        "blocked_judge_aliases": json_dumps(blocked_aliases),
    }


def _routes_for_scores(score_rows: list[dict[str, Any]]) -> list[str]:
    routes: list[str] = []
    for row in score_rows:
        routes.append(route_one(row)["data_route"])
    return routes


def _build_disagreement(
    run_row: dict[str, Any],
    primary_rows: list[dict[str, Any]],
    threshold: float,
) -> dict[str, Any]:
    rates = [float(row.get("score_rate") or 0.0) for row in primary_rows]
    score_gap = round(max(rates) - min(rates), 3) if len(rates) >= 2 else 0.0
    critical_sets = [_critical_tag_set(row) for row in primary_rows]
    routes = _routes_for_scores(primary_rows)
    reasons: list[str] = []
    if len(primary_rows) < 2:
        reasons.append("single_primary_after_self_eval_exclusion")
    if score_gap >= threshold:
        reasons.append("score_gap")
    if len({tuple(sorted(tags)) for tags in critical_sets}) > 1:
        reasons.append("critical_failure_mismatch")
    if len(set(routes)) > 1:
        reasons.append("route_mismatch")
    return {
        "run_id": run_row["run_id"],
        "sample_id": safe_text(run_row["sample_id"]),
        "model_alias": safe_text(run_row.get("model_alias")),
        "version": safe_text(run_row.get("version")),
        "primary_judge_count": len(primary_rows),
        "primary_judges": json_dumps([row["judge_model_alias"] for row in primary_rows]),
        "score_gap": score_gap,
        "primary_score_rates": json_dumps(
            {row["judge_model_alias"]: row["score_rate"] for row in primary_rows}
        ),
        "critical_tag_sets": json_dumps(
            {row["judge_model_alias"]: sorted(_critical_tag_set(row)) for row in primary_rows}
        ),
        "primary_routes": json_dumps(
            {row["judge_model_alias"]: route for row, route in zip(primary_rows, routes)}
        ),
        "requires_arbitration": bool(reasons),
        "disagreement_reasons": "|".join(reasons),
    }


def _build_summary(disagreement: dict[str, Any], score_rows: list[dict[str, Any]]) -> dict[str, Any]:
    arbiter_rows = [row for row in score_rows if row["judge_role"] == "arbiter"]
    selected_rows = arbiter_rows or [row for row in score_rows if row["judge_role"] == "primary"]
    score_rates = [float(row["score_rate"]) for row in selected_rows]
    routes = _routes_for_scores(selected_rows)
    risks = [safe_text(row.get("risk_level")) for row in selected_rows]
    requires_arbitration = bool(disagreement["requires_arbitration"])
    final_route = (
        "human_review" if requires_arbitration and not arbiter_rows else _most_common(routes, "human_review")
    )
    return {
        "run_id": disagreement["run_id"],
        "sample_id": disagreement["sample_id"],
        "model_alias": disagreement["model_alias"],
        "version": disagreement["version"],
        "ensemble_status": (
            "arbitrated" if arbiter_rows else "needs_human_calibration" if requires_arbitration else "stable"
        ),
        "selected_judges": json_dumps([row["judge_model_alias"] for row in selected_rows]),
        "final_score_rate": round(mean(score_rates), 3) if score_rates else 0.0,
        "final_risk_level": _max_risk(risks),
        "final_data_route": final_route,
        "requires_arbitration": requires_arbitration,
        "requires_human_calibration": bool(final_route == "human_review" or (requires_arbitration and not arbiter_rows)),
        "disagreement_reasons": disagreement["disagreement_reasons"],
    }


def run_judge_ensemble(
    *,
    runs: pd.DataFrame,
    bundle: DatasetBundle,
    config: dict[str, Any],
    mode: str,
    output_dir: str | Path,
    prompt_dir: str | Path = "prompts",
) -> dict[str, pd.DataFrame]:
    ensemble = config.get("judge_ensemble") or {}
    primary_judges = ensemble.get("primary_judges") or []
    arbiter = ensemble.get("arbiter") or {}
    if not primary_judges:
        fallback = config.get("judge") or {}
        primary_judges = [dict(fallback, alias=fallback.get("alias") or "single_judge", role="primary")]
    self_eval_exclusion = bool(ensemble.get("self_eval_exclusion", True))
    disagreement_config = ensemble.get("disagreement") or {}
    score_gap_threshold = float(disagreement_config.get("score_gap_threshold", 0.15))
    builder = PromptBuilder(prompt_dir)

    score_rows: list[dict[str, Any]] = []
    disagreement_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for _, run in tqdm(runs.iterrows(), total=len(runs), desc="judge ensemble"):
        run_row = run.to_dict()
        sample_id = safe_text(run_row["sample_id"])
        gold_row = find_gold_row(bundle, sample_id)
        eval_row = find_eval_row(bundle, sample_id)
        blocked_aliases = [
            _judge_alias(judge, idx)
            for idx, judge in enumerate(primary_judges)
            if self_eval_exclusion and _matches_answer_model(judge, run_row)
        ]
        selected_primary = [
            judge
            for judge in primary_judges
            if not (self_eval_exclusion and _matches_answer_model(judge, run_row))
        ]
        if not selected_primary:
            selected_primary = primary_judges[:1]

        primary_rows: list[dict[str, Any]] = []
        for judge_config in selected_primary:
            payload, parsed_ok, raw_judge_output, judge_prompt_id = _judge_payload_for_run(
                run_row=run_row,
                gold_row=gold_row,
                eval_row=eval_row,
                judge_config=judge_config,
                config=config,
                mode=mode,
                builder=builder,
            )
            row = _score_row(
                run_row=run_row,
                eval_row=eval_row,
                payload=payload,
                parsed_ok=parsed_ok,
                raw_judge_output=raw_judge_output,
                judge_prompt_id=judge_prompt_id,
                judge_config=judge_config,
                judge_role="primary",
                blocked_aliases=blocked_aliases,
            )
            primary_rows.append(row)
            score_rows.append(row)

        disagreement = _build_disagreement(run_row, primary_rows, score_gap_threshold)
        all_rows_for_run = list(primary_rows)
        arbiter_blocked = self_eval_exclusion and arbiter and _matches_answer_model(arbiter, run_row)
        if disagreement["requires_arbitration"] and arbiter and not arbiter_blocked:
            payload, parsed_ok, raw_judge_output, judge_prompt_id = _judge_payload_for_run(
                run_row=run_row,
                gold_row=gold_row,
                eval_row=eval_row,
                judge_config=arbiter,
                config=config,
                mode=mode,
                builder=builder,
            )
            arbiter_row = _score_row(
                run_row=run_row,
                eval_row=eval_row,
                payload=payload,
                parsed_ok=parsed_ok,
                raw_judge_output=raw_judge_output,
                judge_prompt_id=judge_prompt_id,
                judge_config=arbiter,
                judge_role="arbiter",
                blocked_aliases=blocked_aliases,
            )
            all_rows_for_run.append(arbiter_row)
            score_rows.append(arbiter_row)
            disagreement["arbiter_judge"] = arbiter_row["judge_model_alias"]
        else:
            disagreement["arbiter_judge"] = ""
            if arbiter_blocked:
                reasons = [disagreement["disagreement_reasons"], "arbiter_self_eval_blocked"]
                disagreement["disagreement_reasons"] = "|".join([reason for reason in reasons if reason])

        disagreement_rows.append(disagreement)
        summary_rows.append(_build_summary(disagreement, all_rows_for_run))

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    scores = pd.DataFrame(score_rows)
    disagreements = pd.DataFrame(disagreement_rows)
    summary = pd.DataFrame(summary_rows)
    scores.to_csv(output_root / "judge_ensemble_scores.csv", index=False, encoding="utf-8-sig")
    disagreements.to_csv(output_root / "judge_disagreements.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(output_root / "judge_ensemble_summary.csv", index=False, encoding="utf-8-sig")
    return {"scores": scores, "disagreements": disagreements, "summary": summary}
