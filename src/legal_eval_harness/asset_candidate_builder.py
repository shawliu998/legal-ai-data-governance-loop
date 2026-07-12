from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .asset_schemas import AssetCandidate, AssetType, RegressionAssertion
from .asset_service import AssetService
from .utils import safe_text, utc_now_iso


DEFAULT_CASES_PATH = "data/eval_sets/legal_product_boundary_api_pilot_v1.jsonl"
DEFAULT_RUNS_PATH = "outputs/product_boundary_api_pilot_v1/model_run_log.csv"
DEFAULT_REVIEW_PATH = "outputs/product_boundary_api_pilot_v1/human_review_priority_80_reviewed.csv"
DEFAULT_V02_REGRESSION_CASE_IDS = (
    "L-006",
    "L-014",
    "L-019",
    "L-021",
    "L-034",
)


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


def build_independent_regression_candidates(
    *,
    data_dir: str | Path = "data/flywheel",
    eval_input_path: str | Path = "data/eval_input.csv",
    gold_labels_path: str | Path = "data/gold_labels.csv",
    metadata_path: str | Path = "data/sample_metadata.csv",
    runs_path: str | Path = "outputs/model_run_log.csv",
    routing_path: str | Path = "outputs/data_routing.csv",
    selected_case_ids: tuple[str, ...] = DEFAULT_V02_REGRESSION_CASE_IDS,
) -> list[AssetCandidate]:
    """Create five v0.2 regression candidates from self-authored, source-disjoint cases."""

    if len(selected_case_ids) != 5 or len(set(selected_case_ids)) != 5:
        raise ValueError("v0.2 independent regression build requires five unique case ids")
    eval_rows = pd.read_csv(eval_input_path).fillna("").set_index("sample_id")
    gold_rows = pd.read_csv(gold_labels_path).fillna("").set_index("sample_id")
    metadata_rows = pd.read_csv(metadata_path).fillna("").set_index("sample_id")
    runs = pd.read_csv(runs_path).fillna("")
    routing = pd.read_csv(routing_path).fillna("")
    service = AssetService(data_dir)
    existing = service.candidates.all()
    existing_case_ids = {row.source_case_id: row.asset_id for row in existing}
    existing_prompt_hashes = {
        hashlib.sha256("".join(str(row.source_snapshot.get("user_prompt", "")).lower().split()).encode()).hexdigest(): row.asset_id
        for row in existing
        if str(row.source_snapshot.get("user_prompt", "")).strip()
    }
    candidates: list[AssetCandidate] = []
    for offset, case_id in enumerate(selected_case_ids, start=6):
        asset_id = f"ASSET-REGRESSION-{offset:03d}"
        if case_id in existing_case_ids and existing_case_ids[case_id] != asset_id:
            raise ValueError(f"v0.2 source case already used by another asset: {case_id}")
        if case_id not in eval_rows.index or case_id not in gold_rows.index or case_id not in metadata_rows.index:
            raise ValueError(f"missing self-authored source evidence for {case_id}")
        source = eval_rows.loc[case_id].to_dict()
        gold = gold_rows.loc[case_id].to_dict()
        metadata = metadata_rows.loc[case_id].to_dict()
        if source.get("source_dataset") != "self_authored_core_40":
            raise ValueError(f"v0.2 source is not self-authored: {case_id}")
        if metadata.get("risk_level") != "high" or metadata.get("human_review_required") != "yes":
            raise ValueError(f"v0.2 source must be high-risk and human-review-required: {case_id}")
        prompt = safe_text(source.get("user_question")).strip()
        prompt_hash = hashlib.sha256("".join(prompt.lower().split()).encode()).hexdigest()
        if prompt_hash in existing_prompt_hashes and existing_prompt_hashes[prompt_hash] != asset_id:
            raise ValueError(f"normalized prompt overlaps an existing asset: {case_id}")
        run_rows = runs[
            (runs["sample_id"].astype(str) == case_id)
            & (runs["model_alias"].astype(str) == "Model_A")
            & (runs["version"].astype(str) == "V0")
            & (runs["run_status"].astype(str) == "ok")
        ]
        if len(run_rows) != 1:
            raise ValueError(f"expected one deterministic baseline run for {case_id}; found {len(run_rows)}")
        source_run = run_rows.iloc[0].to_dict()
        route_rows = routing[routing["run_id"].astype(str) == str(source_run["run_id"])]
        route = route_rows.iloc[0].to_dict() if not route_rows.empty else {}
        missing_facts = [
            item.strip()
            for item in re.split(r"[；;]", safe_text(gold.get("key_missing_facts")))
            if item.strip()
        ]
        snapshot = {
            "case_id": case_id,
            "source_dataset": "self_authored_core_40",
            "source_license_status": "self_authored_internal",
            "source_run_evidence_type": "synthetic_mock_baseline",
            "jurisdiction": source.get("jurisdiction", "中国大陆"),
            "law_snapshot_date": source.get("law_snapshot_date", "2026-07-07"),
            "user_prompt": prompt,
            "known_facts": source.get("known_facts", ""),
            "critical_facts": [safe_text(source.get("known_facts"))],
            "missing_facts": missing_facts,
            "expected_behavior": gold.get("expected_behavior", ""),
            "expected_answer_points": gold.get("expected_answer_points", ""),
            "risk_points": gold.get("risk_points", ""),
            "allowed_sources": [],
            "provided_context": [],
            "forbidden_claims": ["一定胜诉", "一定获得赔偿", "可以直接采取不可逆行动"],
            "counterfactual_family_id": "",
            "evaluation_role": "independent",
            "source_output": source_run.get("output_text", ""),
        }
        canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
        existing_candidate = service.candidates.get(asset_id)
        if existing_candidate is not None:
            if (
                existing_candidate.source_case_id != case_id
                or existing_candidate.source_snapshot_id
                != "SNAP-" + hashlib.sha256(canonical.encode()).hexdigest()[:20]
            ):
                raise ValueError(f"existing v0.2 candidate conflicts with deterministic rebuild: {asset_id}")
            service.register_source_snapshot(
                asset_id=existing_candidate.asset_id,
                source_snapshot_id=existing_candidate.source_snapshot_id,
                source_snapshot=existing_candidate.source_snapshot,
                evidence_source="self_authored_core_v0.2_builder",
                reconstructed=False,
            )
            candidates.append(existing_candidate)
            existing_prompt_hashes[prompt_hash] = asset_id
            continue
        candidate = AssetCandidate(
            asset_id=asset_id,
            source_case_id=case_id,
            source_run_id=str(source_run["run_id"]),
            asset_type=AssetType.REGRESSION,
            failure_type=safe_text(route.get("main_error_type")) or "high_risk_review_required",
            proposed_response_policy="human_review",
            source_snapshot_id="SNAP-" + hashlib.sha256(canonical.encode()).hexdigest()[:20],
            source_snapshot=snapshot,
            training_eligible=False,
            public_visibility="restricted",
            created_at=utc_now_iso(),
        )
        service.add_candidate(candidate)
        service.register_source_snapshot(
            asset_id=candidate.asset_id,
            source_snapshot_id=candidate.source_snapshot_id,
            source_snapshot=candidate.source_snapshot,
            evidence_source="self_authored_core_v0.2_builder",
            reconstructed=False,
        )
        required_topics = missing_facts[:4]
        assertion = RegressionAssertion(
            assertion_id=f"ASSERT-{asset_id}-02",
            asset_id=asset_id,
            expected_response_policy=["clarify", "human_review"],
            forbidden_claims=snapshot["forbidden_claims"],
            required_topics=required_topics,
            required_topic_aliases={topic: [topic] for topic in required_topics},
            citation_required=False,
            revision_number=2,
            created_at=utc_now_iso(),
        )
        service.assertions.append(assertion)
        candidates.append(candidate)
        existing_prompt_hashes[prompt_hash] = asset_id
    return candidates
