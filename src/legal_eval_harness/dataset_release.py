from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .asset_schemas import (
    AssetCandidate,
    AssetStatus,
    DatasetMembership,
    DatasetMembershipStatus,
    DatasetRelease,
    ReviewEvent,
)
from .asset_contamination import cross_split_contamination, overlapping_signals
from .asset_service import AssetService
from .utils import utc_now_iso


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_commit() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return result.stdout.strip() or "unavailable"


def git_is_dirty() -> bool:
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(result.stdout.strip())


def build_code_snapshot(output_path: str | Path) -> dict[str, Any]:
    roots = [
        Path("src/legal_eval_harness"),
        Path("prompts"),
        Path("tests"),
        Path("scripts"),
        Path(".github/workflows"),
    ]
    files = [Path("pyproject.toml"), Path("config.yaml")]
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    entries = {
        path.as_posix(): {"sha256": file_sha256(path), "bytes": path.stat().st_size}
        for path in sorted(set(files))
        if path.exists()
    }
    canonical = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    snapshot = {
        "tree_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "file_count": len(entries),
        "files": entries,
    }
    Path(output_path).write_text(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return snapshot


def build_expert_review_bundle(
    service: AssetService,
    output_path: str | Path = "outputs/flywheel/expert_review_bundle.csv",
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for candidate in service.candidates.all():
        if candidate.asset_status != AssetStatus.EXPERT_REVIEW_PENDING:
            continue
        correction = service.latest_correction(candidate.asset_id)
        correction_history = sorted(
            [row for row in service.corrections.all() if row.asset_id == candidate.asset_id],
            key=lambda row: row.revision_number,
        )
        prior_correction = correction_history[-2] if len(correction_history) > 1 else None
        reviews = {row.review_role: row for row in service.current_reviews_for(candidate.asset_id)}
        final_expert_history = [
            row for row in service.reviews_for(candidate.asset_id) if row.review_role == "final_expert"
        ]
        adjudication = service.current_adjudication_for(candidate.asset_id)
        qa = service.current_quality_check_for(candidate.asset_id)
        rows.append(
            {
                "asset_id": candidate.asset_id,
                "asset_type": candidate.asset_type.value,
                "source_case_id": candidate.source_case_id,
                "source_run_id": candidate.source_run_id,
                "source_snapshot_id": candidate.source_snapshot_id,
                "source_snapshot": json.dumps(candidate.source_snapshot, ensure_ascii=False, sort_keys=True),
                "public_visibility": candidate.public_visibility,
                "user_prompt": candidate.source_snapshot.get("user_prompt", ""),
                "correction_revision": correction.revision_number if correction else "",
                "prior_corrected_answer": prior_correction.corrected_answer if prior_correction else "",
                "prior_expert_feedback": (
                    json.dumps(final_expert_history[-1].findings, ensure_ascii=False)
                    if final_expert_history
                    else ""
                ),
                "corrected_answer": correction.corrected_answer if correction else "",
                "chosen_answer": correction.chosen_answer if correction else "",
                "rejected_answer": correction.rejected_answer if correction else "",
                "preference_reason": correction.preference_reason if correction else "",
                "regression_assertion": (
                    service.assertion_for(candidate.asset_id).model_dump_json()
                    if service.assertion_for(candidate.asset_id)
                    else ""
                ),
                "ai_a_decision": reviews.get("reviewer_a").decision if reviews.get("reviewer_a") else "",
                "ai_a_findings": json.dumps(reviews.get("reviewer_a").findings, ensure_ascii=False)
                if reviews.get("reviewer_a")
                else "",
                "ai_b_decision": reviews.get("reviewer_b").decision if reviews.get("reviewer_b") else "",
                "ai_b_findings": json.dumps(reviews.get("reviewer_b").findings, ensure_ascii=False)
                if reviews.get("reviewer_b")
                else "",
                "ai_conflicts": json.dumps(adjudication.conflicts, ensure_ascii=False) if adjudication else "",
                "ai_adjudication": adjudication.proposed_decision if adjudication else "",
                "ai_adjudication_rationale": adjudication.rationale if adjudication else "",
                "qa_passed": qa.passed if qa else False,
                "qa_findings": json.dumps(qa.findings, ensure_ascii=False) if qa else "",
                "expert_decision": "",
                "expert_override": "",
                "expert_override_reason": "",
                "self_reported_review_entry_seconds": "",
                "reviewer_role": "legal_phd",
            }
        )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(output, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    return df


def finalize_asset(
    service: AssetService,
    asset_id: str,
    *,
    decision: str,
    reason: str,
    review_elapsed_seconds: float,
    reviewer_identifier: str = "legal_phd",
    expert_override: bool = False,
) -> None:
    if decision not in {"accepted", "rework_required", "rejected"}:
        raise ValueError("expert decision must be accepted, rework_required, or rejected")
    candidate = service.candidates.get(asset_id)
    correction = service.latest_correction(asset_id)
    if candidate is None or candidate.asset_status != AssetStatus.EXPERT_REVIEW_PENDING:
        raise ValueError("asset must be expert_review_pending")
    if correction is None:
        raise ValueError("asset must have a current correction")
    review_decision = {"accepted": "approve", "rework_required": "rework", "rejected": "reject"}[decision]
    payload = f"{asset_id}|{decision}|{reason}|{reviewer_identifier}"
    digest = hashlib.sha256(payload.encode()).hexdigest()
    sequence = 1 + sum(row.review_role == "final_expert" for row in service.reviews_for(asset_id))
    event = ReviewEvent(
        event_id=f"REV-{asset_id}-final_expert-{sequence:02d}",
        asset_id=asset_id,
        review_actor_type="legal_expert",
        review_role="final_expert",
        decision=review_decision,
        findings=[reason],
        response_policy=candidate.proposed_response_policy,
        prompt_version="human-final-review-v1",
        model_identifier=reviewer_identifier,
        context_isolation_id=f"HUMAN-{reviewer_identifier}",
        input_hash=digest,
        output_hash=digest,
        review_elapsed_seconds=review_elapsed_seconds,
        expert_override=expert_override,
        expert_override_reason=reason if expert_override else "",
        correction_id=correction.correction_id,
        correction_revision=correction.revision_number,
        source_snapshot_id=candidate.source_snapshot_id,
        corrected_answer_hash=hashlib.sha256(correction.corrected_answer.encode("utf-8")).hexdigest(),
        created_at=utc_now_iso(),
    )
    service.reviews.append(event)
    service.transition(
        asset_id,
        AssetStatus(decision),
        reason=reason,
        actor_type="legal_expert",
    )


def apply_expert_review_bundle(service: AssetService, input_path: str | Path) -> int:
    rows = pd.read_csv(input_path).fillna("").to_dict(orient="records")
    pending_ids = {
        row.asset_id for row in service.candidates.all() if row.asset_status == AssetStatus.EXPERT_REVIEW_PENDING
    }
    submitted_ids = {str(row.get("asset_id")) for row in rows}
    if not rows or len(submitted_ids) != len(rows):
        raise ValueError("expert review bundle must contain unique assets")
    if submitted_ids != pending_ids:
        raise ValueError(
            f"expert review bundle must match all pending assets; missing={sorted(pending_ids - submitted_ids)}, "
            f"unexpected={sorted(submitted_ids - pending_ids)}"
        )
    allowed = {"accepted", "rework_required", "rejected"}
    errors: list[str] = []
    for row in rows:
        asset_id = str(row.get("asset_id", ""))
        decision = str(row.get("expert_decision", "")).strip()
        reason = str(row.get("expert_override_reason", "")).strip()
        override = str(row.get("expert_override", "")).strip().lower()
        try:
            elapsed = float(
                row.get("self_reported_review_entry_seconds")
                or row.get("review_elapsed_seconds", 0)
            )
        except (TypeError, ValueError):
            elapsed = 0
        if decision not in allowed:
            errors.append(f"{asset_id}: invalid or blank expert_decision")
        if not reason:
            errors.append(f"{asset_id}: expert_override_reason is required as the review rationale")
        if override not in {"yes", "no"}:
            errors.append(f"{asset_id}: expert_override must be yes or no")
        if elapsed <= 0:
            errors.append(f"{asset_id}: self_reported_review_entry_seconds must be positive")
        if str(row.get("reviewer_role", "")).strip() != "legal_phd":
            errors.append(f"{asset_id}: reviewer_role must be legal_phd")
    if errors:
        raise ValueError("; ".join(errors))
    for row in rows:
        finalize_asset(
            service,
            str(row["asset_id"]),
            decision=str(row["expert_decision"]).strip(),
            reason=str(row["expert_override_reason"]).strip(),
            review_elapsed_seconds=float(
                row.get("self_reported_review_entry_seconds")
                or row.get("review_elapsed_seconds", 0)
            ),
            reviewer_identifier="legal_phd",
            expert_override=str(row["expert_override"]).strip().lower() == "yes",
        )
    return len(rows)


def build_dataset_release(
    service: AssetService,
    *,
    version: str = "legal_flywheel_v0.1.0",
    output_dir: str | Path | None = None,
) -> DatasetRelease:
    accepted = [row for row in service.candidates.all() if row.asset_status == AssetStatus.ACCEPTED]
    counts = Counter(row.asset_type.value for row in accepted)
    expected = {"sft": 5, "preference": 5, "regression": 5}
    if counts != expected:
        raise ValueError(f"release requires exactly {expected}; found {dict(counts)}")
    root = Path(output_dir or f"outputs/flywheel/{version}")
    root.mkdir(parents=True, exist_ok=True)
    created = utc_now_iso()
    release = DatasetRelease(
        dataset_release_id=version,
        version=version,
        asset_ids=sorted(row.asset_id for row in accepted),
        created_at=created,
        git_commit=git_commit(),
        known_limitations=[
            "Pilot-scale release of 15 assets; not representative of all Chinese legal tasks.",
            "AI pre-review does not replace legal expert approval.",
            "Source snapshots use the repository law snapshot date and require future legal updates.",
        ],
    )
    memberships: list[dict[str, Any]] = []
    membership_models: list[DatasetMembership] = []
    accepted_rows: list[dict[str, Any]] = []
    public_rows: list[dict[str, Any]] = []
    training_assets = [row for row in accepted if row.asset_type.value != "regression"]
    for candidate in sorted(accepted, key=lambda row: row.asset_id):
        split = "train"
        if candidate.asset_type.value == "regression":
            overlaps = [row for row in training_assets if overlapping_signals(row, candidate)]
            if overlaps:
                explicitly_disclosed = (
                    candidate.source_snapshot.get("evaluation_role")
                    == "same_source_bug_reproduction"
                )
                if not explicitly_disclosed and version != "legal_flywheel_v0.1.0":
                    raise ValueError(
                        f"regression source overlaps training data without explicit bug-reproduction status: {candidate.asset_id}"
                    )
                split = "bug_reproduction"
            else:
                split = "test"
        existing_memberships = [
            row
            for row in service.memberships.all()
            if row.asset_id == candidate.asset_id
            and row.dataset_release_id == version
            and row.status == DatasetMembershipStatus.INCLUDED
        ]
        membership = next((row for row in existing_memberships if row.split == split), None)
        if membership is None:
            if existing_memberships:
                stale_ids = {row.dataset_membership_id for row in existing_memberships}
                service.memberships.replace_all(
                    [
                        row.model_copy(update={"status": DatasetMembershipStatus.DEPRECATED})
                        if row.dataset_membership_id in stale_ids
                        else row
                        for row in service.memberships.all()
                    ]
                )
            membership = DatasetMembership(
                asset_id=candidate.asset_id,
                dataset_release_id=version,
                split=split,
                created_at=created,
            )
        included_candidate = service.include(membership)
        memberships.append(membership.model_dump(mode="json"))
        membership_models.append(membership)
        correction = service.latest_correction(candidate.asset_id)
        qa = service.current_quality_check_for(candidate.asset_id)
        adjudication = service.current_adjudication_for(candidate.asset_id)
        record = {
            **included_candidate.model_dump(mode="json"),
            "correction": correction.model_dump(mode="json") if correction else {},
            "review_events": [
                row.model_dump(mode="json") for row in service.current_reviews_for(candidate.asset_id)
            ],
            "adjudication": adjudication.model_dump(mode="json") if adjudication else {},
            "quality_check": qa.model_dump(mode="json") if qa else {},
            "regression_assertion": (
                service.assertion_for(candidate.asset_id).model_dump(mode="json")
                if service.assertion_for(candidate.asset_id)
                else {}
            ),
            "source_snapshot_versions": [
                row.model_dump(mode="json")
                for row in service.source_snapshot_versions.all()
                if row.asset_id == candidate.asset_id
            ],
            "expert_approval_binding": (
                next(
                    (
                        row.model_dump(mode="json")
                        for row in reversed(service.expert_approval_bindings.all())
                        if row.asset_id == candidate.asset_id
                    ),
                    {},
                )
            ),
        }
        accepted_rows.append(record)
        if candidate.public_visibility == "public_redacted":
            public_rows.append(
                {
                    "asset_id": candidate.asset_id,
                    "asset_type": candidate.asset_type.value,
                    "source_case_id": candidate.source_case_id,
                    "corrected_answer": correction.corrected_answer if correction else "",
                    "limitations": "Redacted pilot sample; not legal advice.",
                }
            )
    accepted_path = root / "accepted_assets.jsonl"
    accepted_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in accepted_rows),
        encoding="utf-8",
    )
    memberships_path = root / "dataset_memberships.csv"
    pd.DataFrame(memberships).to_csv(memberships_path, index=False, encoding="utf-8-sig")
    public_path = root / "public_redacted_samples.jsonl"
    public_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in public_rows),
        encoding="utf-8",
    )
    contamination_findings = cross_split_contamination(accepted, membership_models)
    if contamination_findings:
        raise ValueError(f"train/test contamination detected: {contamination_findings}")
    has_test_split = any(row.split == "test" for row in membership_models)
    bug_members = [row for row in membership_models if row.split == "bug_reproduction"]
    contamination_rows = [
        {
            "scope": "train_vs_test",
            "status": "passed" if has_test_split else "not_applicable",
            "signals_checked": (
                "source_case_id,source_snapshot_id,normalized_user_prompt_hash,counterfactual_family_id"
            ),
            "note": (
                "no overlaps detected"
                if has_test_split
                else "no independent test split; same-source regressions are bug_reproduction"
            ),
        }
    ]
    contamination_path = root / "contamination_audit.csv"
    pd.DataFrame(contamination_rows).to_csv(contamination_path, index=False, encoding="utf-8-sig")
    reviews = [
        row
        for asset_id in release.asset_ids
        for row in service.current_reviews_for(asset_id)
    ]
    ai_a = {
        row.asset_id: row
        for row in reviews
        if row.review_role == "reviewer_a" and row.review_protocol_version == "blind-v2"
    }
    ai_b = {
        row.asset_id: row
        for row in reviews
        if row.review_role == "reviewer_b" and row.review_protocol_version == "blind-v2"
    }
    if set(ai_a) != set(release.asset_ids) or set(ai_b) != set(release.asset_ids):
        raise ValueError("release metrics require blind-v2 A/B reviews for all accepted assets")
    exact_fields = (
        "decision",
        "response_policy",
        "legal_conclusion_supported",
        "critical_facts_covered",
        "dangerous_action_advice",
        "citation_support",
        "should_clarify",
        "should_human_review",
    )
    agreements = sum(
        all(getattr(ai_a[aid], field) == getattr(ai_b[aid], field) for field in exact_fields)
        for aid in release.asset_ids
    )
    adjudications = [
        next(
            (
                row
                for row in reversed(service.adjudications.all())
                if row.asset_id == aid and row.review_protocol_version == "blind-v2"
            ),
            None,
        )
        for aid in release.asset_ids
    ]
    experts_by_asset = {
        row.asset_id: row
        for row in reviews
        if row.review_role == "final_expert" and row.asset_id in release.asset_ids
    }
    experts = [experts_by_asset[asset_id] for asset_id in release.asset_ids]
    recorded_override_count = sum(row.expert_override is True for row in experts)
    blind_divergence_count = sum(
        adjudication is not None and adjudication.proposed_decision != "approve"
        for adjudication in adjudications
    )
    transitions = [row for row in service.transitions.all() if row.asset_id in release.asset_ids]
    reworked_assets = {row.asset_id for row in transitions if row.to_status == AssetStatus.REWORK_REQUIRED}
    qa_failures = sum(
        not row.passed for row in service.quality_checks.all() if row.asset_id in release.asset_ids
    )
    metrics = pd.DataFrame(
        [
            {"metric": "accepted_sft", "value": 5},
            {"metric": "accepted_preference", "value": 5},
            {"metric": "accepted_regression", "value": 5},
            {"metric": "ai_exact_agreement_rate", "value": round(agreements / 15, 4)},
            {"metric": "ai_conflict_rate", "value": round(sum(bool(a.conflicts) for a in adjudications if a) / 15, 4)},
            {
                "metric": "recorded_expert_override_rate_legacy",
                "value": round(recorded_override_count / 15, 4),
            },
            {
                "metric": "expert_vs_blind_v2_divergence_rate",
                "value": round(blind_divergence_count / 15, 4),
            },
            {
                "metric": "first_pass_acceptance_rate",
                "value": round((15 - len(reworked_assets)) / 15, 4),
            },
            {"metric": "qa_failure_count", "value": qa_failures},
            {"metric": "regression_pass_rate", "value": "pending"},
            {
                "metric": "median_self_reported_review_entry_seconds",
                "value": float(pd.Series([row.review_elapsed_seconds for row in experts]).median()),
            },
        ]
    )
    metrics_path = root / "metrics_summary.csv"
    metrics.to_csv(metrics_path, index=False, encoding="utf-8-sig")
    code_snapshot_path = root / "code_snapshot.json"
    code_snapshot = build_code_snapshot(code_snapshot_path)
    manifest = {
        **release.model_dump(mode="json"),
        "counts": expected,
        "review_policy": (
            "legacy-v1 A/B pre-reviews preceded item-level legal-PhD final review; "
            "their prior-label contamination is disclosed and excluded from corrected metrics. "
            "Frozen accepted corrections were subsequently re-audited with label-isolated blind-v2 A/B "
            "and conflict consolidation, with exact correction/snapshot/hash binding."
        ),
        "working_tree_dirty_at_build": git_is_dirty(),
        "metric_definitions": {
            "ai_exact_agreement_rate": "share matching on decision, policy, four safety/legal fields, citation support, clarification, and human-review recommendation",
            "ai_conflict_rate": "share with at least one conflict recorded by deterministic consolidation",
            "recorded_expert_override_rate_legacy": "share marked override in submitted expert reviews against legacy label-contaminated AI proposals; retained only as historical evidence",
            "expert_vs_blind_v2_divergence_rate": "share where accepted final expert decision differs from the independently rerun blind-v2 proposed adjudication",
            "first_pass_acceptance_rate": "share accepted without any rework_required transition",
            "qa_failure_count": "number of failed QA events, including superseded revisions",
            "regression_pass_rate": "passed real reruns divided by five; populated after regression execution",
            "median_self_reported_review_entry_seconds": "median reviewer-entered duration; not instrumented active review time",
        },
        "split_policy": {
            "independent_test_assets": sum(row.split == "test" for row in membership_models),
            "same_source_bug_reproductions": len(bug_members),
            "cross_split_contamination_check": (
                "passed" if has_test_split else "not_applicable_no_independent_test_split"
            ),
            "signals_checked": [
                "source_case_id",
                "source_snapshot_id",
                "normalized_user_prompt_hash",
                "counterfactual_family_id",
            ],
        },
        "code_snapshot": {
            "path": code_snapshot_path.name,
            "tree_sha256": code_snapshot["tree_sha256"],
            "file_count": code_snapshot["file_count"],
        },
        "files": {},
    }
    for path in (
        accepted_path,
        memberships_path,
        contamination_path,
        metrics_path,
        public_path,
        code_snapshot_path,
    ):
        manifest["files"][path.name] = {"sha256": file_sha256(path), "bytes": path.stat().st_size}
    (root / "release_manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return release


def refresh_release_after_regression(root: str | Path) -> None:
    release_root = Path(root)
    manifest_path = release_root / "release_manifest.yaml"
    metrics_path = release_root / "metrics_summary.csv"
    results_path = release_root / "regression_results.csv"
    if not (manifest_path.exists() and metrics_path.exists() and results_path.exists()):
        raise ValueError("release manifest, metrics, and regression results must exist")
    results = pd.read_csv(results_path).fillna("")
    if len(results) != 5 or results["rerun_id"].astype(str).str.strip().eq("").any():
        raise ValueError("exactly five regression rows with rerun_id are required")
    metrics = pd.read_csv(metrics_path, dtype={"value": "object"})
    pass_rate = round(float((results["regression_status"] == "passed").mean()), 4)
    attempts = set(results["rerun_attempt_number"])
    if len(attempts) != 1:
        raise ValueError("official regression view must contain one attempt number")
    official_attempt = int(next(iter(attempts)))
    attempt_dir = release_root / "regression_attempts" / f"attempt_{official_attempt:02d}"
    run_log_path = attempt_dir / "regression_run_log.jsonl"
    if not run_log_path.exists():
        raise ValueError(f"immutable run log missing for attempt {official_attempt}")
    ledger_path = release_root / "regression_attempt_events.jsonl"
    if not ledger_path.exists():
        raise ValueError("regression_attempt_events.jsonl is required")
    metrics.loc[metrics["metric"] == "regression_pass_rate", "value"] = str(pass_rate)
    metrics.to_csv(metrics_path, index=False, encoding="utf-8-sig")
    metric_map = dict(zip(metrics["metric"], metrics["value"], strict=False))
    report_lines = [
        "# legal_flywheel_v0.1.0 metrics report",
        "",
        "## Release result and split boundary",
        "",
        "The release contains 15 accepted assets: 5 SFT, 5 preference, and 5 regression bug reproductions.",
        "The SFT and preference assets are train members. Because the five regression assets reuse SFT source",
        "cases, they are classified as `bug_reproduction`, not an independent test split. Consequently the",
        "cross-split contamination result is `not_applicable_no_independent_test_split`; no claim of an",
        "independent regression-set estimate is made.",
        "",
        "Future standard candidate builds require disjoint train/test sources and compare `source_case_id`,",
        "`source_snapshot_id`, normalized user-prompt hash, and counterfactual family ID.",
        "",
        "## Observed workflow metrics",
        "",
        "| Metric | Value | Interpretation |",
        "| --- | ---: | --- |",
        f"| Blind-v2 AI exact agreement rate | {float(metric_map.get('ai_exact_agreement_rate', 0)):.2%} | Label-isolated A/B exact agreement. |",
        f"| Blind-v2 AI conflict rate | {float(metric_map.get('ai_conflict_rate', 0)):.2%} | At least one deterministic conflict field. |",
        f"| Expert vs blind-v2 divergence rate | {float(metric_map.get('expert_vs_blind_v2_divergence_rate', 0)):.2%} | Workflow divergence, not model ranking. |",
        f"| Self-reported review entry median | {metric_map.get('median_self_reported_review_entry_seconds', '')} seconds | Reviewer-entered duration; not instrumented active review time. |",
        f"| Official bug-reproduction pass rate | {pass_rate:.2%} | Five real attempt-{official_attempt} reruns; strict product gates, not legal accuracy. |",
        "",
        "## Official bug-reproduction reruns",
        "",
        "| Asset | Result | Failed gate |",
        "| --- | --- | --- |",
    ]
    for row in results.to_dict(orient="records"):
        report_lines.append(
            f"| {row['asset_id']} | {row['regression_status']} | {str(row.get('failure_reason') or 'none').replace('_', ' ')} |"
        )
    report_lines.extend(
        [
            "",
            f"Attempt {official_attempt} is the official V5/W4 view. Immutable attempt directories and the",
            "append-only `regression_attempt_events.jsonl` are the system of record; `regression_results.csv`",
            "is only the current official view. Failed results are retained and are not legal-correctness scores.",
            "",
            "## Evidence boundary",
            "",
            "This pilot is not a representative Chinese-law corpus, legal service, independent test estimate,",
            "or model leaderboard. Full prompts, outputs, expert submissions, and lineage evidence remain restricted.",
            "",
        ]
    )
    (release_root / "metrics_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    for path in sorted(release_root.rglob("*")):
        if path.is_file() and path != manifest_path:
            relative_name = path.relative_to(release_root).as_posix()
            manifest.setdefault("files", {})[relative_name] = {
                "sha256": file_sha256(path),
                "bytes": path.stat().st_size,
            }
    manifest["regression_summary"] = {
        "official_attempt": official_attempt,
        "rerun_count": 5,
        "passed": int((results["regression_status"] == "passed").sum()),
        "failed": int((results["regression_status"] == "failed").sum()),
        "pass_rate": pass_rate,
    }
    manifest_path.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def validate_dataset_release(path: str | Path) -> list[str]:
    root = Path(path)
    manifest_path = root / "release_manifest.yaml"
    if not manifest_path.exists():
        return ["missing release_manifest.yaml"]
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    errors: list[str] = []
    for name, metadata in (manifest.get("files") or {}).items():
        target = root / name
        if not target.exists():
            errors.append(f"missing {name}")
        elif file_sha256(target) != metadata.get("sha256"):
            errors.append(f"hash mismatch for {name}")
    assets_path = root / "accepted_assets.jsonl"
    if assets_path.exists():
        rows = [json.loads(line) for line in assets_path.read_text(encoding="utf-8").splitlines() if line]
        candidate_models = [AssetCandidate.model_validate(row) for row in rows]
        memberships_path = root / "dataset_memberships.csv"
        if not memberships_path.exists():
            errors.append("missing dataset_memberships.csv")
            membership_models: list[DatasetMembership] = []
        else:
            membership_models = [
                DatasetMembership.model_validate(row)
                for row in pd.read_csv(memberships_path).fillna("").to_dict(orient="records")
            ]
            contamination = cross_split_contamination(candidate_models, membership_models)
            if contamination:
                errors.append(f"train/test contamination detected: {contamination}")
        split_by_asset = {
            row.asset_id: row.split
            for row in membership_models
            if row.status == DatasetMembershipStatus.INCLUDED
        }
        counts = Counter(row["asset_type"] for row in rows)
        if counts != {"sft": 5, "preference": 5, "regression": 5}:
            errors.append(f"invalid accepted asset counts: {dict(counts)}")
        for row in rows:
            asset_id = row.get("asset_id")
            if row.get("asset_status") != "accepted":
                errors.append(f"asset not accepted: {asset_id}")
            correction = row.get("correction") or {}
            if not str(correction.get("corrected_answer", "")).strip():
                errors.append(f"missing corrected answer: {asset_id}")
            review_events = row.get("review_events", [])
            roles = {event.get("review_role") for event in review_events}
            if not {"reviewer_a", "reviewer_b", "final_expert"}.issubset(roles):
                errors.append(f"missing required review roles: {asset_id}")
            blind_reviews = [
                event for event in review_events if event.get("review_protocol_version") == "blind-v2"
            ]
            blind_roles = {event.get("review_role") for event in blind_reviews}
            if not {"reviewer_a", "reviewer_b"}.issubset(blind_roles):
                errors.append(f"missing blind-v2 review roles: {asset_id}")
            else:
                correction_hash = hashlib.sha256(
                    str(correction.get("corrected_answer", "")).encode("utf-8")
                ).hexdigest()
                for event in blind_reviews:
                    if event.get("corrected_answer_hash") != correction_hash:
                        errors.append(f"blind review correction hash mismatch: {asset_id}")
                    if event.get("correction_id") != correction.get("correction_id"):
                        errors.append(f"blind review correction id mismatch: {asset_id}")
                    if event.get("correction_revision") != correction.get("revision_number"):
                        errors.append(f"blind review correction revision mismatch: {asset_id}")
                    if event.get("source_snapshot_id") != row.get("source_snapshot_id"):
                        errors.append(f"blind review source snapshot mismatch: {asset_id}")
                    raw_evidence = root / "blind_review_evidence" / str(asset_id) / f"{event.get('review_role')}.json"
                    if not raw_evidence.exists():
                        errors.append(f"missing blind raw output evidence: {asset_id}/{event.get('review_role')}")
                    else:
                        raw_record = json.loads(raw_evidence.read_text(encoding="utf-8"))
                        if raw_record.get("output_hash") != event.get("output_hash"):
                            errors.append(f"blind raw output hash mismatch: {asset_id}/{event.get('review_role')}")
            final = [event for event in row.get("review_events", []) if event.get("review_role") == "final_expert"]
            if not final or final[-1].get("decision") != "approve":
                errors.append(f"missing final expert approval: {asset_id}")
            elif final[-1].get("review_actor_type") != "legal_expert":
                errors.append(f"final approval is not from legal_expert: {asset_id}")
            elif (
                final[-1].get("correction_id") != correction.get("correction_id")
                or final[-1].get("correction_revision") != correction.get("revision_number")
                or final[-1].get("source_snapshot_id") != row.get("source_snapshot_id")
                or final[-1].get("corrected_answer_hash")
                != hashlib.sha256(
                    str(correction.get("corrected_answer", "")).encode("utf-8")
                ).hexdigest()
            ):
                errors.append(f"final expert lineage mismatch: {asset_id}")
            quality = row.get("quality_check") or {}
            required_quality = (
                "pii_check",
                "duplicate_check",
                "source_traceability",
                "contamination_check",
                "law_effective_date_check",
                "type_specific_check",
            )
            if any(
                quality.get(field) != "passed"
                for field in required_quality
                if field != "contamination_check"
            ) or quality.get("contamination_check") not in {"passed", "not_applicable"}:
                errors.append(f"final QA not passed: {asset_id}")
            if (
                quality.get("correction_id") != correction.get("correction_id")
                or quality.get("correction_revision") != correction.get("revision_number")
                or quality.get("source_snapshot_id") != row.get("source_snapshot_id")
                or quality.get("corrected_answer_hash")
                != hashlib.sha256(
                    str(correction.get("corrected_answer", "")).encode("utf-8")
                ).hexdigest()
            ):
                errors.append(f"final QA lineage mismatch: {asset_id}")
            adjudication = row.get("adjudication") or {}
            if adjudication.get("status") not in {"not_required", "proposed_adjudication"}:
                errors.append(f"missing adjudication evidence: {asset_id}")
            elif adjudication.get("review_protocol_version") != "blind-v2":
                errors.append(f"final adjudication is not blind-v2: {asset_id}")
            elif (
                adjudication.get("correction_id") != correction.get("correction_id")
                or adjudication.get("correction_revision") != correction.get("revision_number")
                or adjudication.get("source_snapshot_id") != row.get("source_snapshot_id")
                or adjudication.get("corrected_answer_hash")
                != hashlib.sha256(
                    str(correction.get("corrected_answer", "")).encode("utf-8")
                ).hexdigest()
            ):
                errors.append(f"final adjudication lineage mismatch: {asset_id}")
            binding = row.get("expert_approval_binding") or {}
            if not binding:
                errors.append(f"missing expert approval binding: {asset_id}")
            else:
                if binding.get("correction_id") != correction.get("correction_id"):
                    errors.append(f"expert binding correction id mismatch: {asset_id}")
                if binding.get("corrected_answer_hash") != hashlib.sha256(
                    str(correction.get("corrected_answer", "")).encode("utf-8")
                ).hexdigest():
                    errors.append(f"expert binding answer hash mismatch: {asset_id}")
                if binding.get("source_snapshot_id") != row.get("source_snapshot_id"):
                    errors.append(f"expert binding source snapshot mismatch: {asset_id}")
                evidence_path = root / "review_evidence" / Path(
                    str(binding.get("submission_file", ""))
                ).name
                if not evidence_path.exists():
                    errors.append(f"missing expert submission evidence: {asset_id}")
                elif file_sha256(evidence_path) != binding.get("submission_file_sha256"):
                    errors.append(f"expert submission hash mismatch: {asset_id}")
            if not row.get("source_snapshot_versions"):
                errors.append(f"missing source snapshot version lineage: {asset_id}")
            if row.get("dataset_membership_status") != "included":
                errors.append(f"asset not marked included: {asset_id}")
            if asset_id not in split_by_asset:
                errors.append(f"asset missing included membership: {asset_id}")
            if row.get("asset_type") == "regression" and split_by_asset.get(asset_id) not in {
                "test",
                "bug_reproduction",
            }:
                errors.append(f"invalid regression split: {asset_id}")
            if row.get("asset_type") == "regression" and not row.get("regression_assertion"):
                errors.append(f"missing regression assertion: {asset_id}")
        contamination_path = root / "contamination_audit.csv"
        if not contamination_path.exists():
            errors.append("missing contamination_audit.csv")
        else:
            audit = pd.read_csv(contamination_path).fillna("")
            if len(audit) != 1 or set(audit.get("status", [])) - {"passed", "not_applicable"}:
                errors.append("invalid contamination audit")
    regression_path = root / "regression_results.csv"
    if not regression_path.exists():
        errors.append("missing regression_results.csv")
    else:
        results = pd.read_csv(regression_path).fillna("")
        if len(results) != 5:
            errors.append(f"expected 5 regression results; found {len(results)}")
        if "rerun_id" not in results or results["rerun_id"].astype(str).str.strip().eq("").any():
            errors.append("regression results contain blank rerun_id")
        elif results["rerun_id"].nunique() != len(results):
            errors.append("regression rerun_id values are not unique")
        if "regression_status" not in results or not set(results["regression_status"]).issubset(
            {"passed", "failed"}
        ):
            errors.append("invalid regression_status values")
        if "scoring_revision" not in results or set(results["scoring_revision"]) != {"scoring-v2"}:
            errors.append("official regression results are not uniformly scoring-v2")
        attempt_numbers = set(results.get("rerun_attempt_number", []))
        if len(attempt_numbers) != 1:
            errors.append("official regression results must reference exactly one attempt")
            official_attempt = 0
        else:
            official_attempt = int(next(iter(attempt_numbers)))
        manifest_attempt = (manifest.get("regression_summary") or {}).get("official_attempt")
        if manifest_attempt != official_attempt:
            errors.append(
                f"official attempt mismatch: csv={official_attempt}, manifest={manifest_attempt}"
            )
        attempt_dir = root / "regression_attempts" / f"attempt_{official_attempt:02d}"
        run_log_path = attempt_dir / "regression_run_log.jsonl"
        if not run_log_path.exists():
            errors.append("missing regression_run_log.jsonl")
        else:
            run_logs = [
                json.loads(line)
                for line in run_log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if len(run_logs) != 5:
                errors.append(f"expected 5 regression run logs; found {len(run_logs)}")
            elif {str(row.get("rerun_id")) for row in run_logs} != set(results["rerun_id"].astype(str)):
                errors.append("regression result and run-log rerun_id sets differ")
        ledger_path = root / "regression_attempt_events.jsonl"
        if not ledger_path.exists():
            errors.append("missing regression_attempt_events.jsonl")
        else:
            events = [
                json.loads(line)
                for line in ledger_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            recorded = {
                int(row.get("attempt_number", 0))
                for row in events
                if row.get("event_type") == "attempt_recorded"
            }
            for event in events:
                if event.get("event_type") != "attempt_recorded":
                    continue
                event_dir = root / str(event.get("attempt_path", ""))
                for name, expected_hash in (event.get("file_sha256") or {}).items():
                    evidence = event_dir / name
                    if not evidence.exists():
                        errors.append(f"attempt evidence missing: {event.get('attempt_path')}/{name}")
                    elif file_sha256(evidence) != expected_hash:
                        errors.append(f"immutable attempt evidence hash mismatch: {event.get('attempt_path')}/{name}")
            directories = {
                int(path.name.split("_")[-1])
                for path in (root / "regression_attempts").glob("attempt_*")
                if path.is_dir()
            }
            if recorded != directories:
                errors.append(
                    f"attempt ledger/directory mismatch: ledger={sorted(recorded)}, dirs={sorted(directories)}"
                )
            selected = {
                int(row.get("attempt_number", 0))
                for row in events
                if row.get("event_type") == "official_attempt_selected"
            }
            if official_attempt not in selected:
                errors.append("official attempt has no append-only selection event")
        report_path = root / "metrics_report.md"
        if not report_path.exists():
            errors.append("missing metrics_report.md")
        else:
            import re

            report_attempts = {
                int(value)
                for value in re.findall(r"Five real attempt-(\d+) reruns", report_path.read_text(encoding="utf-8"))
            }
            if report_attempts != {official_attempt}:
                errors.append(
                    f"report attempt mismatch: report={sorted(report_attempts)}, official={official_attempt}"
                )
    metrics_path = root / "metrics_summary.csv"
    if not metrics_path.exists():
        errors.append("missing metrics_summary.csv")
    elif regression_path.exists():
        metrics = pd.read_csv(metrics_path).fillna("")
        metric_map = dict(zip(metrics["metric"], metrics["value"], strict=False))
        observed = round(float((pd.read_csv(regression_path)["regression_status"] == "passed").mean()), 4)
        try:
            reported = float(metric_map.get("regression_pass_rate", -1))
        except (TypeError, ValueError):
            reported = -1
        if reported != observed:
            errors.append(f"regression pass rate mismatch: metrics={reported}, observed={observed}")
    code_snapshot_path = root / "code_snapshot.json"
    if not code_snapshot_path.exists():
        errors.append("missing code_snapshot.json")
    else:
        code_snapshot = json.loads(code_snapshot_path.read_text(encoding="utf-8"))
        entries = code_snapshot.get("files") or {}
        for name, metadata in entries.items():
            source = Path(name)
            if not source.exists():
                errors.append(f"code snapshot source missing: {name}")
            elif file_sha256(source) != metadata.get("sha256"):
                errors.append(f"code snapshot source drift: {name}")
    return errors
