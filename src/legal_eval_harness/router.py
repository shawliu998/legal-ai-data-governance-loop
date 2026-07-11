from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .schemas import (
    COARSE_ERROR_TAGS,
    DATA_ASSET_ROUTES,
    DATA_ROUTES,
    RESPONSE_POLICIES,
    WORKFLOW_STATUSES,
    WORKFLOW_TRANSITIONS,
)
from .utils import json_dumps, json_loads_or_none, parse_bool, safe_text


BLOCKING_TAGS = {"fabricated_citation", "unsafe_action_suggestion"}
GROUNDING_TAGS = {"missing_evidence_warning", "unverified_basis"}
ERROR_PRIORITY = [
    "fabricated_citation",
    "unsafe_action_suggestion",
    "unverified_basis",
    "overclaim",
    "missing_facts",
    "missing_evidence_warning",
    "missing_procedure_warning",
    "jurisdiction_risk",
    "weak_fact_rule_application",
    "needs_human_review",
]


def _parse_tags(value: Any) -> list[dict[str, str]]:
    parsed = json_loads_or_none(value) or []
    tags: list[dict[str, str]] = []
    for item in parsed:
        if isinstance(item, str):
            coarse = item if item in COARSE_ERROR_TAGS else "needs_human_review"
            tags.append({"coarse_error_tag": coarse, "error_subtype": ""})
        elif isinstance(item, dict):
            coarse = safe_text(item.get("coarse_error_tag"))
            subtype = safe_text(item.get("error_subtype"))
            if coarse not in COARSE_ERROR_TAGS:
                coarse = "needs_human_review"
                subtype = subtype or "non_standard_error_tag"
            tags.append({"coarse_error_tag": coarse, "error_subtype": subtype})
    return tags


def _requires_grounding(row: dict[str, Any], coarse_tags: list[str]) -> bool:
    if any(parse_bool(row.get(field)) for field in ["retrieval_required", "citation_required", "rag_enabled"]):
        return True
    if safe_text(row.get("retrieval_status")).lower() in {"hit", "retrieved", "success"}:
        return True
    source_ids = json_loads_or_none(row.get("rag_source_ids")) or []
    return bool(source_ids) or bool(set(coarse_tags).intersection(GROUNDING_TAGS))


def _asset_routes(coarse_tags: list[str]) -> list[str]:
    routes: set[str] = set()
    tag_set = set(coarse_tags)
    if tag_set.intersection(BLOCKING_TAGS | {"unverified_basis", "needs_human_review"}):
        routes.update({"badcase", "regression"})
    if "overclaim" in tag_set:
        routes.update({"preference", "regression"})
    if tag_set.intersection({"missing_facts", "missing_evidence_warning", "missing_procedure_warning"}):
        routes.add("sft")
    if tag_set.intersection({"weak_fact_rule_application", "jurisdiction_risk"}) or not tag_set:
        routes.add("eval")
    if not routes:
        routes.add("eval")
    return [route for route in DATA_ASSET_ROUTES if route in routes]


def _main_error(coarse_tags: list[str]) -> str:
    return next((tag for tag in ERROR_PRIORITY if tag in coarse_tags), "no_detected_error")


def route_one(score_row: dict[str, Any]) -> dict[str, Any]:
    tags = _parse_tags(score_row.get("error_tags"))
    coarse_tags = [tag["coarse_error_tag"] for tag in tags]
    risk_level = safe_text(score_row.get("risk_level")) or "medium"
    judge_confidence = safe_text(score_row.get("judge_confidence")) or "medium"
    needs_review = parse_bool(score_row.get("needs_human_review"))
    try:
        score_rate = float(score_row.get("score_rate") or 0)
    except (TypeError, ValueError):
        score_rate = 0.0
    parsed_ok = parse_bool(score_row.get("parsed_ok"), default=True)
    run_failed = safe_text(score_row.get("run_status")).lower() in {
        "failed",
        "error",
        "timeout",
        "empty_output",
    }

    blocking_subtype = any(
        tag["error_subtype"] in {"model_run_failed", "empty_model_output"} for tag in tags
    )
    blocking = bool(set(coarse_tags).intersection(BLOCKING_TAGS)) or run_failed or blocking_subtype
    review_required = (
        risk_level == "high"
        or judge_confidence == "low"
        or needs_review
        or not parsed_ok
    )
    asset_routes = _asset_routes(coarse_tags)
    main_error = _main_error(coarse_tags)

    if blocking or review_required:
        route = "human_review"
        if run_failed and main_error == "no_detected_error":
            main_error = "run_failed"
        reason = "Blocking failure or review-control signal requires human calibration before reuse."
    elif "overclaim" in coarse_tags:
        route = "badcase" if score_rate < 0.66 else "preference"
        main_error = "overclaim"
        reason = "Overclaim behavior is useful for preference comparison or badcase regression."
    elif "missing_facts" in coarse_tags:
        route = "sft" if score_rate < 0.75 else "eval"
        main_error = "missing_facts"
        reason = "Missing-facts awareness can be converted into intake/checklist training or held-out eval."
    elif "missing_evidence_warning" in coarse_tags:
        route = "sft"
        main_error = "missing_evidence_warning"
        reason = "Evidence-risk warning should become risk-control SFT material."
    elif "weak_fact_rule_application" in coarse_tags:
        route = "eval"
        main_error = "weak_fact_rule_application"
        reason = "Weak fact-rule application should remain in targeted diagnostic eval."
    else:
        route = "eval"
        reason = "Default route for diagnostic tracking."

    if blocking:
        response_policy = "block"
    elif review_required:
        response_policy = "human_review"
    elif "missing_facts" in coarse_tags:
        response_policy = "clarify"
    elif _requires_grounding(score_row, coarse_tags):
        response_policy = "grounded_answer"
    else:
        response_policy = "auto_answer"
    workflow_status = {
        "block": "blocked",
        "human_review": "pending_review",
    }.get(response_policy, "released")

    if route not in DATA_ROUTES:
        raise AssertionError(f"Non-standard route generated: {route}")
    if workflow_status not in WORKFLOW_STATUSES or response_policy not in RESPONSE_POLICIES:
        raise AssertionError("Invalid workflow status or response policy generated")

    priority = (
        "P0"
        if response_policy in {"block", "human_review"} or risk_level == "high"
        else "P1"
        if risk_level == "medium"
        else "P2"
    )
    subtype = next((tag["error_subtype"] for tag in tags if tag["coarse_error_tag"] == main_error), "")
    candidate_for_reuse = parsed_ok and not run_failed and bool(asset_routes)
    requires_correction = bool(coarse_tags) or response_policy in {"block", "human_review", "clarify"}
    # Initial routing never approves gold. Gold is a post-review state set only
    # by apply_review_adjudications after explicit reviewer approval.
    gold_approved = False
    return {
        "sample_id": score_row["sample_id"],
        "run_id": score_row["run_id"],
        "source_dataset": score_row.get("source_dataset", ""),
        "task_category": score_row.get("task_category", ""),
        "model_alias": score_row.get("model_alias", ""),
        "version": score_row.get("version", ""),
        "main_error_type": main_error,
        "error_tags": tags,
        "risk_level": risk_level,
        "workflow_status": workflow_status,
        "response_policy": response_policy,
        # Backward-compatible alias; do not use for group-level release gates.
        "release_decision": response_policy,
        "data_asset_routes": asset_routes,
        "data_route": route,
        "route_reason": reason,
        "route_subtype": subtype,
        "priority": priority,
        "candidate_for_reuse": candidate_for_reuse,
        "requires_correction": requires_correction,
        "gold_approved": gold_approved,
        "reusable_as_gold_sample": gold_approved,
    }


def _serialize_routing_frame(frame: pd.DataFrame) -> pd.DataFrame:
    serialized = frame.copy()
    for column in ["error_tags", "data_asset_routes"]:
        if column in serialized.columns:
            serialized[column] = serialized[column].map(
                lambda value: json_dumps(json_loads_or_none(value) or [])
            )
    return serialized


def apply_review_adjudications(
    *,
    routing: pd.DataFrame,
    adjudications: pd.DataFrame,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    """Apply reviewer decisions while keeping workflow, release, and gold separate."""
    if "run_id" not in routing.columns or "run_id" not in adjudications.columns:
        raise ValueError("routing and adjudications must include run_id")
    if adjudications["run_id"].astype(str).duplicated().any():
        raise ValueError("adjudications must contain at most one row per run_id")

    result = routing.copy()
    for column in ["error_tags", "data_asset_routes"]:
        if column in result.columns:
            result[column] = result[column].map(lambda value: json_loads_or_none(value) or [])
    if "response_policy" not in result.columns:
        legacy = result.get("release_decision", pd.Series("", index=result.index)).fillna("")
        result["response_policy"] = legacy.where(
            legacy.isin(RESPONSE_POLICIES),
            result.get("data_route", pd.Series("eval", index=result.index)).map(
                lambda value: "human_review" if value == "human_review" else "auto_answer"
            ),
        )
    if "workflow_status" not in result.columns:
        result["workflow_status"] = result["response_policy"].map(
            {"block": "blocked", "human_review": "pending_review"}
        ).fillna("released")
    for column, default in [
        ("candidate_for_reuse", False),
        ("requires_correction", True),
        ("gold_approved", False),
        ("reusable_as_gold_sample", False),
    ]:
        if column not in result.columns:
            result[column] = default

    result_ids = set(result["run_id"].astype(str))
    unknown_ids = set(adjudications["run_id"].astype(str)) - result_ids
    if unknown_ids:
        raise ValueError(f"adjudications reference unknown run_id values: {sorted(unknown_ids)}")

    by_run_id = {str(row["run_id"]): row for _, row in adjudications.iterrows()}
    for index, decision in result.iterrows():
        adjudication = by_run_id.get(str(decision["run_id"]))
        if adjudication is None:
            continue

        current_status = safe_text(decision.get("workflow_status")) or "pending_review"
        if current_status not in WORKFLOW_TRANSITIONS:
            raise ValueError(f"invalid current workflow_status for {decision['run_id']}: {current_status}")

        response_policy = safe_text(adjudication.get("adjudicated_triage_label"))
        if not response_policy:
            response_policy = safe_text(decision.get("response_policy"))
        if response_policy not in RESPONSE_POLICIES:
            raise ValueError(f"invalid adjudicated_triage_label for {decision['run_id']}: {response_policy}")

        reviewer_approved = parse_bool(adjudication.get("reviewer_approved"))
        correction_completed = parse_bool(adjudication.get("correction_completed"))
        needs_correction = parse_bool(decision.get("requires_correction")) and not correction_completed
        requested_status = safe_text(adjudication.get("target_workflow_status"))
        if requested_status:
            target_status = requested_status
        elif response_policy == "block":
            target_status = "blocked"
        elif reviewer_approved:
            target_status = "released"
        else:
            target_status = "reviewed"

        if target_status not in WORKFLOW_STATUSES:
            raise ValueError(f"invalid target_workflow_status for {decision['run_id']}: {target_status}")
        if target_status not in WORKFLOW_TRANSITIONS[current_status]:
            raise ValueError(
                f"invalid workflow transition for {decision['run_id']}: {current_status} -> {target_status}"
            )
        if target_status == "released":
            if not reviewer_approved:
                raise ValueError(f"release requires explicit reviewer approval for {decision['run_id']}")
            if needs_correction:
                raise ValueError(f"release requires correction completion for {decision['run_id']}")
            if response_policy in {"human_review", "block"}:
                raise ValueError(
                    f"released rows require an answerable adjudicated policy for {decision['run_id']}"
                )
        if target_status == "blocked" and response_policy != "block":
            raise ValueError(f"blocked status requires block policy for {decision['run_id']}")

        gold_requested = parse_bool(
            adjudication.get("gold_approved"),
            default=parse_bool(adjudication.get("reviewer_gold_approved")),
        )
        gold_approved = bool(
            gold_requested
            and reviewer_approved
            and not needs_correction
            and parse_bool(decision.get("candidate_for_reuse"))
            and target_status == "released"
            and response_policy in {"auto_answer", "grounded_answer"}
        )

        result.at[index, "workflow_status"] = target_status
        result.at[index, "response_policy"] = response_policy
        result.at[index, "release_decision"] = response_policy
        result.at[index, "requires_correction"] = needs_correction
        result.at[index, "reviewer_approved"] = reviewer_approved
        result.at[index, "correction_completed"] = correction_completed
        result.at[index, "gold_approval_requested"] = gold_requested
        result.at[index, "gold_approved"] = gold_approved
        result.at[index, "reusable_as_gold_sample"] = gold_approved
        for column in [
            "adjudicated_triage_label",
            "adjudication_mode",
            "reviewer_a_id",
            "reviewer_b_id",
            "reviewed_at",
        ]:
            if column in adjudications.columns:
                result.at[index, column] = adjudication.get(column, "")

    if output_path is not None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        _serialize_routing_frame(result).to_csv(output_path, index=False, encoding="utf-8-sig")
    return result


def route_scores(
    *,
    judge_scores: pd.DataFrame,
    output_path: str | Path,
    runs: pd.DataFrame | None = None,
) -> pd.DataFrame:
    scores = judge_scores.copy()
    if runs is not None and not runs.empty:
        if "run_id" not in runs.columns:
            raise ValueError("runs must include run_id")
        signal_columns = [
            field
            for field in [
                "run_id",
                "run_status",
                "retrieval_required",
                "citation_required",
                "rag_enabled",
                "rag_source_ids",
                "retrieval_status",
            ]
            if field in runs.columns
        ]
        run_signals = runs[signal_columns].drop_duplicates("run_id", keep="last")
        scores = scores.merge(run_signals, on="run_id", how="left", suffixes=("", "_run"))
        for field in signal_columns:
            run_field = f"{field}_run"
            if run_field not in scores.columns:
                continue
            if field not in scores.columns:
                scores[field] = scores[run_field]
            else:
                missing = scores[field].isna() | scores[field].astype(str).str.strip().eq("")
                scores.loc[missing, field] = scores.loc[missing, run_field]
            scores = scores.drop(columns=[run_field])

    rows = [route_one(row.to_dict()) for _, row in scores.iterrows()]
    df = pd.DataFrame(rows)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    _serialize_routing_frame(df).to_csv(output_path, index=False, encoding="utf-8-sig")
    return df
