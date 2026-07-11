from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd

from .utils import json_dumps, json_loads_or_none, parse_bool, safe_text


CRITICAL_TAGS = {"fabricated_citation", "unsafe_action_suggestion", "needs_human_review"}
RESPONSE_POLICIES = {"auto_answer", "grounded_answer", "clarify", "human_review", "block"}


def _coarse_tags(value: Any) -> list[str]:
    parsed = json_loads_or_none(value) or []
    tags: list[str] = []
    for item in parsed:
        if isinstance(item, dict):
            tag = safe_text(item.get("coarse_error_tag"))
        else:
            tag = safe_text(item)
        if tag:
            tags.append(tag)
    return tags


def _is_critical(row: pd.Series) -> bool:
    tags = set(_coarse_tags(row.get("error_tags")))
    return (
        safe_text(row.get("risk_level")) == "high"
        or safe_text(row.get("judge_confidence")) == "low"
        or parse_bool(row.get("needs_human_review"))
        or bool(tags.intersection(CRITICAL_TAGS))
    )


def _canonical_routing(routing: pd.DataFrame) -> pd.DataFrame:
    """Accept legacy routing CSVs while exposing the canonical dimensions."""
    result = routing.copy()
    if "data_route" not in result.columns:
        result["data_route"] = "eval"
    if "response_policy" not in result.columns:
        legacy = result.get("release_decision", pd.Series("", index=result.index)).fillna("")
        result["response_policy"] = legacy.where(
            legacy.isin(RESPONSE_POLICIES),
            result["data_route"].map(lambda value: "human_review" if value == "human_review" else "auto_answer"),
        )
    if "workflow_status" not in result.columns:
        result["workflow_status"] = result["response_policy"].map(
            {"block": "blocked", "human_review": "pending_review"}
        ).fillna("released")
    if "data_asset_routes" not in result.columns:
        result["data_asset_routes"] = result["data_route"].map(
            lambda value: [value]
            if value in {"eval", "sft", "preference", "badcase", "regression"}
            else []
        )
    return result


def _stratified_sample(
    frame: pd.DataFrame,
    *,
    n: int,
    random_state: int,
    strata_columns: list[str],
) -> pd.DataFrame:
    if n <= 0 or frame.empty:
        return frame.head(0)
    n = min(n, len(frame))
    strata = [col for col in strata_columns if col in frame.columns]
    if not strata:
        return frame.sample(n=n, random_state=random_state)

    sampled_parts = []
    groups = frame.groupby(strata, dropna=False)
    per_stratum = max(1, math.ceil(n / max(1, groups.ngroups)))
    for _, group in groups:
        sampled_parts.append(group.sample(n=min(per_stratum, len(group)), random_state=random_state))
    sampled = pd.concat(sampled_parts, ignore_index=False) if sampled_parts else frame.head(0)
    sampled = sampled.drop_duplicates("run_id")
    if len(sampled) > n:
        sampled = sampled.sample(n=n, random_state=random_state)
    return sampled


def build_human_review_sample(
    *,
    runs: pd.DataFrame,
    scores: pd.DataFrame,
    routing: pd.DataFrame,
    output_path: str | Path,
    citation_verification: pd.DataFrame | None = None,
    ensemble_summary: pd.DataFrame | None = None,
    sample_rate: float = 0.2,
    min_samples: int = 20,
    random_calibration_min: int = 0,
    random_state: int = 7,
) -> pd.DataFrame:
    if not 0 < sample_rate <= 1:
        raise ValueError("sample_rate must be in (0, 1]")
    if random_calibration_min < 0:
        raise ValueError("random_calibration_min must be non-negative")

    run_subset = runs.copy()
    if "workflow_condition" not in run_subset.columns:
        run_subset["workflow_condition"] = run_subset.get("version", "")
        run_subset["workflow_name"] = run_subset.get("version", "")
    for col in ["model_vendor", "model_family", "latency_ms", "estimated_cost"]:
        if col not in run_subset.columns:
            run_subset[col] = 0 if col in {"latency_ms", "estimated_cost"} else ""
    routing = _canonical_routing(routing)
    merged = scores.merge(
        routing[
            [
                "run_id",
                "workflow_status",
                "response_policy",
                "data_asset_routes",
                "data_route",
                "main_error_type",
                "route_reason",
                "priority",
            ]
        ],
        on="run_id",
        how="left",
    ).merge(
        run_subset[
            [
                "run_id",
                "model_vendor",
                "model_family",
                "workflow_condition",
                "workflow_name",
                "output_text",
                "latency_ms",
                "estimated_cost",
            ]
        ],
        on="run_id",
        how="left",
    )
    if citation_verification is not None and not citation_verification.empty:
        citation_cols = [
            col
            for col in [
                "run_id",
                "citation_fidelity_label",
                "fabricated_citation_count",
                "unsupported_claim_count",
                "claim_count",
                "claim_checks",
            ]
            if col in citation_verification.columns
        ]
        merged = merged.merge(citation_verification[citation_cols], on="run_id", how="left")
    if ensemble_summary is not None and not ensemble_summary.empty:
        ensemble_cols = [
            col
            for col in [
                "run_id",
                "ensemble_status",
                "final_response_policy",
                "final_data_route",
                "requires_arbitration",
                "requires_human_calibration",
                "disagreement_reasons",
            ]
            if col in ensemble_summary.columns
        ]
        merged = merged.merge(ensemble_summary[ensemble_cols], on="run_id", how="left")

    merged["critical_for_review"] = merged.apply(_is_critical, axis=1)
    citation_label = merged.get("citation_fidelity_label", pd.Series("", index=merged.index)).fillna("")
    merged["citation_or_claim_review"] = citation_label.isin(
        ["fabricated_citation", "missing_citation", "unsupported_claim"]
    )
    merged["ensemble_review"] = merged.get(
        "requires_human_calibration", pd.Series(False, index=merged.index)
    ).map(parse_bool)
    merged["legal_review_required"] = (
        merged["critical_for_review"] | merged["citation_or_claim_review"] | merged["ensemble_review"]
    )
    target = min(len(merged), max(min_samples, math.ceil(len(merged) * sample_rate)))

    selected = merged[merged["legal_review_required"]].copy()
    if len(selected) < target:
        remaining = merged[~merged["run_id"].isin(selected["run_id"])].copy()
        sampled = _stratified_sample(
            remaining,
            n=target - len(selected),
            random_state=random_state,
            strata_columns=["task_category", "model_alias", "workflow_condition", "risk_level"],
        )
        selected = pd.concat([selected, sampled], ignore_index=False)

    if len(selected) > target and not selected["legal_review_required"].all():
        critical = selected[selected["legal_review_required"]]
        non_critical = selected[~selected["legal_review_required"]]
        keep_non_critical = max(0, target - len(critical))
        if keep_non_critical:
            non_critical = non_critical.sample(n=keep_non_critical, random_state=random_state)
        else:
            non_critical = non_critical.head(0)
        selected = pd.concat([critical, non_critical], ignore_index=False)

    if random_calibration_min:
        current_random = int((~selected["legal_review_required"]).sum())
        random_needed = max(0, random_calibration_min - current_random)
        if random_needed:
            remaining = merged[~merged["run_id"].isin(selected["run_id"]) & ~merged["legal_review_required"]].copy()
            sampled = _stratified_sample(
                remaining,
                n=random_needed,
                random_state=random_state,
                strata_columns=["task_category", "model_alias", "workflow_condition", "risk_level"],
            )
            selected = pd.concat([selected, sampled], ignore_index=False)

    selected = selected.sort_values(
        [
            "legal_review_required",
            "critical_for_review",
            "citation_or_claim_review",
            "ensemble_review",
            "task_category",
            "risk_level",
            "sample_id",
            "model_alias",
            "version",
        ],
        ascending=[False, False, False, False, True, True, True, True, True],
    ).copy()
    selected["review_bucket"] = selected.apply(
        lambda row: (
            "critical_failure"
            if row.get("critical_for_review")
            else "citation_or_claim"
            if row.get("citation_or_claim_review")
            else "judge_disagreement"
            if row.get("ensemble_review")
            else "random_calibration"
        ),
        axis=1,
    )
    selected["auto_triage_label"] = selected["response_policy"]
    selected["reviewer_a_id"] = ""
    selected["reviewer_a_triage_label"] = ""
    selected["reviewer_b_id"] = ""
    selected["reviewer_b_triage_label"] = ""
    selected["adjudicated_triage_label"] = ""
    selected["adjudication_mode"] = ""
    selected["agreement_type"] = ""
    # Legacy single-reviewer fields remain for old calibration sheets.
    selected["legal_reviewer_id"] = ""
    selected["human_pass_fail"] = ""
    selected["human_corrected_score_rate"] = ""
    selected["human_critical_failure"] = ""
    selected["human_citation_support"] = ""
    selected["human_unsupported_claims"] = ""
    selected["human_route_override"] = ""
    selected["human_data_action"] = ""
    selected["human_notes"] = ""
    selected["judge_human_agreement"] = ""

    columns = [
        "run_id",
        "sample_id",
        "source_dataset",
        "task_category",
        "model_alias",
        "model_vendor",
        "model_family",
        "version",
        "workflow_condition",
        "workflow_name",
        "score_rate",
        "risk_level",
        "judge_confidence",
        "needs_human_review",
        "workflow_status",
        "response_policy",
        "data_asset_routes",
        "data_route",
        "main_error_type",
        "priority",
        "review_bucket",
        "legal_review_required",
        "critical_for_review",
        "citation_or_claim_review",
        "ensemble_review",
        "citation_fidelity_label",
        "fabricated_citation_count",
        "unsupported_claim_count",
        "claim_count",
        "claim_checks",
        "ensemble_status",
        "final_response_policy",
        "requires_human_calibration",
        "disagreement_reasons",
        "latency_ms",
        "estimated_cost",
        "judge_reason",
        "output_text",
        "auto_triage_label",
        "reviewer_a_id",
        "reviewer_a_triage_label",
        "reviewer_b_id",
        "reviewer_b_triage_label",
        "adjudicated_triage_label",
        "adjudication_mode",
        "agreement_type",
        "legal_reviewer_id",
        "human_pass_fail",
        "human_corrected_score_rate",
        "human_critical_failure",
        "human_citation_support",
        "human_unsupported_claims",
        "human_route_override",
        "human_data_action",
        "human_notes",
        "judge_human_agreement",
    ]
    for col in columns:
        if col not in selected.columns:
            selected[col] = ""
    result = selected[columns].reset_index(drop=True)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    serialized = result.copy()
    if "data_asset_routes" in serialized.columns:
        serialized["data_asset_routes"] = serialized["data_asset_routes"].map(
            lambda value: json_dumps(json_loads_or_none(value) or [])
        )
    serialized.to_csv(output_path, index=False, encoding="utf-8-sig")
    return result


def summarize_human_calibration(*, reviewed: pd.DataFrame, output_path: str | Path) -> pd.DataFrame:
    def filled(column: str) -> pd.Series:
        if column not in reviewed.columns:
            return pd.Series(False, index=reviewed.index)
        return reviewed[column].fillna("").map(lambda value: bool(safe_text(value)))

    reviewed_mask = (
        filled("human_pass_fail")
        | filled("human_corrected_score_rate")
        | filled("human_critical_failure")
        | filled("human_citation_support")
        | filled("human_unsupported_claims")
        | filled("human_route_override")
        | filled("human_notes")
    )
    agreement_values = reviewed.get("judge_human_agreement", pd.Series("", index=reviewed.index)).fillna("")
    agreement_normalized = agreement_values.map(lambda value: safe_text(value).lower())
    agreement_reviewed = agreement_normalized[agreement_normalized != ""]
    agreed = agreement_reviewed.isin({"agree", "agreed", "agree_prelim", "yes", "true", "1", "一致"})
    critical_values = reviewed.get("human_critical_failure", pd.Series("", index=reviewed.index)).fillna("")
    critical_confirmed = critical_values.map(lambda value: safe_text(value).lower()).isin(
        {"yes", "yes_prelim", "true", "1", "confirmed", "是", "有"}
    )
    citation_values = reviewed.get("human_citation_support", pd.Series("", index=reviewed.index)).fillna("")
    citation_issue = citation_values.map(lambda value: safe_text(value).lower()).isin(
        {
            "unsupported",
            "unsupported_fabricated_citation",
            "unsupported_needs_legal_review",
            "partial_support_needs_legal_review",
            "missing_citation_needs_review",
            "no",
            "false",
            "0",
            "不支持",
            "引用不支持",
        }
    )
    route_override_values = reviewed.get("human_route_override", pd.Series("", index=reviewed.index)).fillna("")
    route_override_count = route_override_values.map(lambda value: safe_text(value).lower()).map(
        lambda value: bool(value) and value not in {"no_override", "none", "keep", "不调整"}
    )

    reviewer_a = reviewed.get(
        "reviewer_a_triage_label", pd.Series("", index=reviewed.index)
    ).fillna("").map(safe_text)
    reviewer_b = reviewed.get(
        "reviewer_b_triage_label", pd.Series("", index=reviewed.index)
    ).fillna("").map(safe_text)
    reviewer_pair_mask = reviewer_a.ne("") & reviewer_b.ne("")
    pair_a = reviewer_a[reviewer_pair_mask]
    pair_b = reviewer_b[reviewer_pair_mask]
    observed_agreement = float((pair_a == pair_b).mean()) if len(pair_a) else None
    if len(pair_a):
        labels = sorted(set(pair_a).union(pair_b))
        expected_agreement = sum(
            float((pair_a == label).mean() * (pair_b == label).mean()) for label in labels
        )
        reviewer_kappa = (
            (observed_agreement - expected_agreement) / (1 - expected_agreement)
            if expected_agreement < 1
            else 1.0
        )
    else:
        reviewer_kappa = None

    auto_triage = reviewed.get(
        "auto_triage_label", pd.Series("", index=reviewed.index)
    ).fillna("").map(safe_text)
    adjudicated = reviewed.get(
        "adjudicated_triage_label", pd.Series("", index=reviewed.index)
    ).fillna("").map(safe_text)
    adjudicated_mask = auto_triage.ne("") & adjudicated.ne("")
    judge_adjudicated_agreement = (
        float((auto_triage[adjudicated_mask] == adjudicated[adjudicated_mask]).mean())
        if int(adjudicated_mask.sum())
        else None
    )
    result = pd.DataFrame(
        [
            {
                "total_review_rows": len(reviewed),
                "completed_review_rows": int(reviewed_mask.sum()),
                "review_completion_rate": round(float(reviewed_mask.mean()), 3) if len(reviewed) else 0.0,
                "agreement_labeled_rows": int(len(agreement_reviewed)),
                "agreement_basis": "legacy manually supplied judge_human_agreement labels; not reviewer IAA",
                "judge_human_overall_triage_agreement_rate": (
                    round(float(agreed.mean()), 3) if len(agreement_reviewed) else ""
                ),
                "judge_human_agreement_rate": round(float(agreed.mean()), 3) if len(agreement_reviewed) else "",
                "reviewer_pair_labeled_rows": int(reviewer_pair_mask.sum()),
                "reviewer_observed_agreement_rate": (
                    round(observed_agreement, 3) if observed_agreement is not None else ""
                ),
                "reviewer_cohen_kappa": round(reviewer_kappa, 3) if reviewer_kappa is not None else "",
                "judge_adjudicated_labeled_rows": int(adjudicated_mask.sum()),
                "judge_adjudicated_agreement_rate": (
                    round(judge_adjudicated_agreement, 3)
                    if judge_adjudicated_agreement is not None
                    else ""
                ),
                "confirmed_critical_failure_count": int(critical_confirmed.sum()),
                "confirmed_citation_issue_count": int(citation_issue.sum()),
                "human_route_override_count": int(route_override_count.sum()),
                "human_data_action_count": int(filled("human_data_action").sum()),
            }
        ]
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    return result
