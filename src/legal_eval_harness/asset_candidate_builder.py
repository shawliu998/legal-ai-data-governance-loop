from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .asset_schemas import AssetCandidate, AssetType, RegressionAssertion
from .asset_service import AssetService
from .utils import safe_text, utc_now_iso


DEFAULT_CASES_PATH = "data/eval_sets/legal_product_boundary_api_pilot_v1.jsonl"
DEFAULT_RUNS_PATH = "outputs/product_boundary_api_pilot_v1/model_run_log.csv"
DEFAULT_REVIEW_PATH = "outputs/product_boundary_api_pilot_v1/human_review_priority_80_reviewed.csv"


def _load_cases(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def build_asset_candidates(
    *,
    data_dir: str | Path = "data/flywheel",
    cases_path: str | Path = DEFAULT_CASES_PATH,
    runs_path: str | Path = DEFAULT_RUNS_PATH,
    reviewed_path: str | Path = DEFAULT_REVIEW_PATH,
    allow_same_source_bug_reproduction: bool = False,
) -> list[AssetCandidate]:
    """Build 15 candidates, with disjoint train/test sources unless bug reproduction is explicit."""

    cases = {str(row["case_id"]): row for row in _load_cases(cases_path)}
    runs = pd.read_csv(runs_path).fillna("")
    reviewed = pd.read_csv(reviewed_path).fillna("")
    # Human-reviewed failures first, one source run per case.
    reviewed["severity"] = reviewed["human_pass_fail"].map({"fail": 0, "partial": 1, "pass": 2}).fillna(3)
    reviewed = reviewed.sort_values(["severity", "priority", "sample_id", "run_id"])
    source_by_case: dict[str, dict[str, Any]] = {}
    for row in reviewed.to_dict(orient="records"):
        case_id = str(row["sample_id"])
        if case_id in cases and case_id not in source_by_case:
            source_by_case[case_id] = row
    minimum = 10 if allow_same_source_bug_reproduction else 15
    if len(source_by_case) < minimum:
        raise ValueError(
            f"fewer than {minimum} evidenced source cases are available; "
            "pass allow_same_source_bug_reproduction=True only for a non-independent bug-reproduction set"
        )
    selected_ids = list(source_by_case)[:minimum]
    run_by_id = {str(row["run_id"]): row for row in runs.to_dict(orient="records")}
    regression_ids = selected_ids[:5] if allow_same_source_bug_reproduction else selected_ids[10:15]
    specs = (
        [(AssetType.SFT, case_id) for case_id in selected_ids[:5]]
        + [(AssetType.PREFERENCE, case_id) for case_id in selected_ids[5:10]]
        + [(AssetType.REGRESSION, case_id) for case_id in regression_ids]
    )
    service = AssetService(data_dir)
    candidates: list[AssetCandidate] = []
    counters = {AssetType.SFT: 0, AssetType.PREFERENCE: 0, AssetType.REGRESSION: 0}
    for asset_type, case_id in specs:
        counters[asset_type] += 1
        source_review = source_by_case[case_id]
        source_run_id = str(source_review["run_id"])
        source_run = run_by_id.get(source_run_id, {})
        if asset_type == AssetType.PREFERENCE and not safe_text(
            source_run.get("output_text") or source_review.get("output_text")
        ).strip():
            alternatives = reviewed[
                (reviewed["sample_id"].astype(str) == case_id)
                & (reviewed["output_text"].map(safe_text).str.strip() != "")
            ]
            if alternatives.empty:
                raise ValueError(f"preference candidate {case_id} has no non-empty reviewed rejected answer")
            source_review = alternatives.iloc[0].to_dict()
            source_run_id = str(source_review["run_id"])
            source_run = run_by_id.get(source_run_id, {})
        case = cases[case_id]
        snapshot = {
            "case_id": case_id,
            "jurisdiction": case.get("jurisdiction", "CN"),
            "law_snapshot_date": "2026-07-07",
            "user_prompt": case.get("user_prompt", ""),
            "expected_behavior": case.get("expected_behavior", ""),
            "critical_facts": case.get("critical_facts", []),
            "missing_facts": case.get("missing_facts", []),
            "allowed_sources": case.get("allowed_sources", []),
            "provided_context": case.get("provided_context", []),
            "forbidden_claims": case.get("forbidden_claims", []),
            "counterfactual_family_id": case.get("counterfactual_family_id")
            or case.get("pair_id")
            or "",
            "evaluation_role": (
                "same_source_bug_reproduction"
                if asset_type == AssetType.REGRESSION and allow_same_source_bug_reproduction
                else "independent"
            ),
            "expected_human_review": bool(case.get("expected_human_review", False)),
            "source_output": safe_text(source_run.get("output_text") or source_review.get("output_text")),
            "human_pass_fail": safe_text(source_review.get("human_pass_fail")),
            "human_notes": safe_text(source_review.get("human_notes")),
        }
        canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
        snapshot_id = "SNAP-" + hashlib.sha256(canonical.encode()).hexdigest()[:20]
        asset_id = f"ASSET-{asset_type.value.upper()}-{counters[asset_type]:03d}"
        existing = service.candidates.get(asset_id)
        if existing is not None:
            candidates.append(existing)
            continue
        expected_review = snapshot["expected_human_review"]
        candidate = AssetCandidate(
            asset_id=asset_id,
            source_case_id=case_id,
            source_run_id=source_run_id,
            asset_type=asset_type,
            failure_type=safe_text(source_review.get("human_failure_type_zh"))
            or safe_text(source_review.get("main_error_type"))
            or "review_required",
            proposed_response_policy="human_review" if expected_review else "clarify",
            source_snapshot_id=snapshot_id,
            source_snapshot=snapshot,
            training_eligible=asset_type != AssetType.REGRESSION,
            public_visibility="public_redacted" if counters[asset_type] == 1 else "restricted",
            created_at=utc_now_iso(),
        )
        service.add_candidate(candidate)
        if asset_type == AssetType.REGRESSION:
            assertion = RegressionAssertion(
                assertion_id=f"ASSERT-{asset_id}-01",
                asset_id=asset_id,
                expected_response_policy=["clarify", "human_review"],
                forbidden_claims=[safe_text(item) for item in snapshot["forbidden_claims"]],
                required_topics=[safe_text(item) for item in snapshot["missing_facts"][:4]],
                citation_required=bool(snapshot["allowed_sources"]),
                created_at=utc_now_iso(),
            )
            service.assertions.append(assertion)
        candidates.append(candidate)
    return candidates


def build_replacement_candidate(
    *,
    asset_id: str,
    asset_type: AssetType,
    case_id: str,
    data_dir: str | Path = "data/flywheel",
    cases_path: str | Path = DEFAULT_CASES_PATH,
    runs_path: str | Path = DEFAULT_RUNS_PATH,
    reviewed_path: str | Path = DEFAULT_REVIEW_PATH,
) -> AssetCandidate:
    service = AssetService(data_dir)
    existing = service.candidates.get(asset_id)
    if existing is not None:
        return existing
    cases = {str(row["case_id"]): row for row in _load_cases(cases_path)}
    if case_id not in cases:
        raise ValueError(f"unknown replacement case: {case_id}")
    if case_id in {row.source_case_id for row in service.candidates.all()}:
        raise ValueError(f"replacement case is already used: {case_id}")
    reviewed = pd.read_csv(reviewed_path).fillna("")
    alternatives = reviewed[
        (reviewed["sample_id"].astype(str) == case_id)
        & (reviewed["output_text"].map(safe_text).str.strip() != "")
    ].copy()
    if alternatives.empty:
        raise ValueError(f"replacement case has no non-empty reviewed response: {case_id}")
    alternatives["severity"] = alternatives["human_pass_fail"].map(
        {"fail": 0, "partial": 1, "pass": 2}
    ).fillna(3)
    source_review = alternatives.sort_values(["severity", "run_id"]).iloc[0].to_dict()
    runs = pd.read_csv(runs_path).fillna("")
    run_rows = runs[runs["run_id"].astype(str) == str(source_review["run_id"])]
    source_run = run_rows.iloc[0].to_dict() if not run_rows.empty else {}
    case = cases[case_id]
    snapshot = {
        "case_id": case_id,
        "jurisdiction": case.get("jurisdiction", "CN"),
        "law_snapshot_date": "2026-07-07",
        "user_prompt": case.get("user_prompt", ""),
        "expected_behavior": case.get("expected_behavior", ""),
        "critical_facts": case.get("critical_facts", []),
        "missing_facts": case.get("missing_facts", []),
        "allowed_sources": case.get("allowed_sources", []),
        "provided_context": case.get("provided_context", []),
        "forbidden_claims": case.get("forbidden_claims", []),
        "expected_human_review": bool(case.get("expected_human_review", False)),
        "source_output": safe_text(source_run.get("output_text") or source_review.get("output_text")),
        "human_pass_fail": safe_text(source_review.get("human_pass_fail")),
        "human_notes": safe_text(source_review.get("human_notes")),
        "replacement_for": "ASSET-PREFERENCE-003",
        "evaluation_role": "independent",
        "counterfactual_family_id": case.get("counterfactual_family_id")
        or case.get("pair_id")
        or "",
    }
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    candidate = AssetCandidate(
        asset_id=asset_id,
        source_case_id=case_id,
        source_run_id=str(source_review["run_id"]),
        asset_type=asset_type,
        failure_type=safe_text(source_review.get("human_failure_type_zh"))
        or safe_text(source_review.get("main_error_type"))
        or "review_required",
        proposed_response_policy="human_review" if snapshot["expected_human_review"] else "clarify",
        source_snapshot_id="SNAP-" + hashlib.sha256(canonical.encode()).hexdigest()[:20],
        source_snapshot=snapshot,
        training_eligible=asset_type != AssetType.REGRESSION,
        public_visibility="restricted",
        created_at=utc_now_iso(),
    )
    service.add_candidate(candidate)
    return candidate
