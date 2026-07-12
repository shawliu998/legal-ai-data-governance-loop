from __future__ import annotations

import hashlib
from pathlib import Path

from .asset_repository import JsonlRepository
from .asset_schemas import (
    Adjudication,
    AssetCandidate,
    AssetStatus,
    Correction,
    DatasetMembership,
    DatasetMembershipStatus,
    ExpertApprovalBinding,
    QualityCheck,
    RegressionAssertion,
    RegressionResult,
    RegressionStatus,
    ReviewEvent,
    SourceSnapshotVersion,
    StateTransitionEvent,
)
from .asset_state_machine import validate_asset_transition
from .utils import utc_now_iso


class AssetService:
    def __init__(self, data_dir: str | Path = "data/flywheel") -> None:
        root = Path(data_dir)
        self.root = root
        self.candidates = JsonlRepository(root / "asset_candidates.jsonl", AssetCandidate, "asset_id")
        self.corrections = JsonlRepository(root / "corrections.jsonl", Correction, "correction_id")
        self.reviews = JsonlRepository(root / "review_events.jsonl", ReviewEvent, "event_id")
        self.adjudications = JsonlRepository(root / "adjudications.jsonl", Adjudication, "adjudication_id")
        self.quality_checks = JsonlRepository(root / "quality_checks.jsonl", QualityCheck, "quality_check_id")
        self.assertions = JsonlRepository(root / "regression_assertions.jsonl", RegressionAssertion, "assertion_id")
        self.regression_results = JsonlRepository(
            root / "regression_results.jsonl", RegressionResult, "regression_id"
        )
        self.transitions = JsonlRepository(root / "state_transitions.jsonl", StateTransitionEvent, "event_id")
        self.memberships = JsonlRepository(
            root / "dataset_memberships.jsonl", DatasetMembership, "dataset_membership_id"
        )
        self.source_snapshot_versions = JsonlRepository(
            root / "source_snapshot_versions.jsonl", SourceSnapshotVersion, "snapshot_version_id"
        )
        self.expert_approval_bindings = JsonlRepository(
            root / "expert_approval_bindings.jsonl", ExpertApprovalBinding, "binding_id"
        )

    def add_candidate(self, candidate: AssetCandidate) -> bool:
        return self.candidates.append(candidate)

    def update_candidate_source(
        self,
        asset_id: str,
        *,
        source_run_id: str,
        source_snapshot_id: str,
        source_snapshot: dict,
    ) -> AssetCandidate:
        candidate = self._require_candidate(asset_id)
        self.register_source_snapshot(
            asset_id=asset_id,
            source_snapshot_id=candidate.source_snapshot_id,
            source_snapshot=candidate.source_snapshot,
            evidence_source="pre_update_candidate_state",
            reconstructed=False,
        )
        updated = candidate.model_copy(
            update={
                "source_run_id": source_run_id,
                "source_snapshot_id": source_snapshot_id,
                "source_snapshot": source_snapshot,
            }
        )
        self.candidates.replace_all(
            [updated if item.asset_id == asset_id else item for item in self.candidates.all()]
        )
        self.register_source_snapshot(
            asset_id=asset_id,
            source_snapshot_id=source_snapshot_id,
            source_snapshot=source_snapshot,
            evidence_source="update_candidate_source",
            reconstructed=False,
        )
        return updated

    def register_source_snapshot(
        self,
        *,
        asset_id: str,
        source_snapshot_id: str,
        source_snapshot: dict,
        evidence_source: str,
        reconstructed: bool,
        created_at: str | None = None,
    ) -> SourceSnapshotVersion:
        import json

        canonical = json.dumps(source_snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        existing = [row for row in self.source_snapshot_versions.all() if row.asset_id == asset_id]
        same = next((row for row in existing if row.source_snapshot_hash == digest), None)
        if same is not None:
            return same
        row = SourceSnapshotVersion(
            snapshot_version_id=f"SSV-{asset_id}-{len(existing) + 1:02d}-{digest[:10]}",
            asset_id=asset_id,
            source_snapshot_id=source_snapshot_id,
            version_number=len(existing) + 1,
            source_snapshot_hash=digest,
            source_snapshot=source_snapshot,
            evidence_source=evidence_source,
            reconstructed=reconstructed,
            created_at=created_at or utc_now_iso(),
        )
        self.source_snapshot_versions.append(row)
        return row

    def latest_correction(self, asset_id: str) -> Correction | None:
        rows = [row for row in self.corrections.all() if row.asset_id == asset_id]
        return max(rows, key=lambda row: row.revision_number) if rows else None

    def has_stored_correction_for_current_draft(self, asset_id: str) -> bool:
        correction = self.latest_correction(asset_id)
        starts = [
            row
            for row in self.transitions.all()
            if row.asset_id == asset_id and row.to_status == AssetStatus.CORRECTION_DRAFTING
        ]
        return bool(
            correction is not None
            and starts
            and correction.created_at >= starts[-1].created_at
        )

    def reviews_for(self, asset_id: str) -> list[ReviewEvent]:
        return [row for row in self.reviews.all() if row.asset_id == asset_id]

    @staticmethod
    def _matches_lineage(record: object, candidate: AssetCandidate, correction: Correction) -> bool:
        answer_hash = hashlib.sha256(correction.corrected_answer.encode("utf-8")).hexdigest()
        return (
            getattr(record, "correction_id", "") == correction.correction_id
            and getattr(record, "correction_revision", 0) == correction.revision_number
            and getattr(record, "source_snapshot_id", "") == candidate.source_snapshot_id
            and getattr(record, "corrected_answer_hash", "") == answer_hash
        )

    def current_reviews_for(self, asset_id: str) -> list[ReviewEvent]:
        candidate = self._require_candidate(asset_id)
        correction = self.latest_correction(asset_id)
        if correction is None:
            return []
        return [
            row
            for row in self.reviews_for(asset_id)
            if self._matches_lineage(row, candidate, correction)
        ]

    def adjudication_for(self, asset_id: str) -> Adjudication | None:
        rows = [row for row in self.adjudications.all() if row.asset_id == asset_id]
        return rows[-1] if rows else None

    def current_adjudication_for(self, asset_id: str) -> Adjudication | None:
        candidate = self._require_candidate(asset_id)
        correction = self.latest_correction(asset_id)
        if correction is None:
            return None
        rows = [
            row
            for row in self.adjudications.all()
            if row.asset_id == asset_id and self._matches_lineage(row, candidate, correction)
        ]
        return rows[-1] if rows else None

    def quality_check_for(self, asset_id: str) -> QualityCheck | None:
        rows = [row for row in self.quality_checks.all() if row.asset_id == asset_id]
        return rows[-1] if rows else None

    def current_quality_check_for(self, asset_id: str) -> QualityCheck | None:
        candidate = self._require_candidate(asset_id)
        correction = self.latest_correction(asset_id)
        if correction is None:
            return None
        rows = [
            row
            for row in self.quality_checks.all()
            if row.asset_id == asset_id and self._matches_lineage(row, candidate, correction)
        ]
        return rows[-1] if rows else None

    def assertion_for(self, asset_id: str) -> RegressionAssertion | None:
        rows = [row for row in self.assertions.all() if row.asset_id == asset_id]
        return rows[-1] if rows else None

    def transition(
        self,
        asset_id: str,
        target: AssetStatus,
        *,
        reason: str,
        actor_type: str = "system",
    ) -> AssetCandidate:
        candidate = self._require_candidate(asset_id)
        validate_asset_transition(candidate.asset_status, target)
        self._validate_target(candidate, target)
        sequence = 1 + sum(
            row.asset_id == asset_id and row.from_status == candidate.asset_status and row.to_status == target
            for row in self.transitions.all()
        )
        event_id = hashlib.sha256(
            f"{asset_id}|{candidate.asset_status.value}|{target.value}|{reason}|{sequence}".encode()
        ).hexdigest()[:24]
        event = StateTransitionEvent(
            event_id=f"STE-{event_id}",
            asset_id=asset_id,
            from_status=candidate.asset_status,
            to_status=target,
            reason=reason,
            actor_type=actor_type,
            created_at=utc_now_iso(),
        )
        self.transitions.append(event)
        updated = candidate.model_copy(update={"asset_status": target})
        items = [updated if item.asset_id == asset_id else item for item in self.candidates.all()]
        self.candidates.replace_all(items)
        return updated

    def include(self, membership: DatasetMembership) -> AssetCandidate:
        candidate = self._require_candidate(membership.asset_id)
        if candidate.asset_status != AssetStatus.ACCEPTED:
            raise ValueError("only accepted assets can be included in a dataset release")
        if not membership.dataset_release_id or not membership.split:
            raise ValueError("included membership requires release id and split")
        self.memberships.append(membership)
        updated = candidate.model_copy(
            update={"dataset_membership_status": DatasetMembershipStatus.INCLUDED}
        )
        self.candidates.replace_all(
            [updated if item.asset_id == candidate.asset_id else item for item in self.candidates.all()]
        )
        return updated

    def record_regression_result(self, result: RegressionResult) -> AssetCandidate:
        candidate = self._require_candidate(result.asset_id)
        if candidate.asset_type.value != "regression":
            raise ValueError("regression results can only be recorded for regression assets")
        if candidate.asset_status != AssetStatus.ACCEPTED:
            raise ValueError("regression execution requires an accepted asset")
        if candidate.dataset_membership_status != DatasetMembershipStatus.INCLUDED:
            raise ValueError("regression execution requires included dataset membership")
        if self.assertion_for(candidate.asset_id) is None:
            raise ValueError("regression execution requires assertions")
        if not result.rerun_id.strip():
            raise ValueError("regression result requires a real rerun_id")
        self.regression_results.append(result)
        updated = candidate.model_copy(
            update={"regression_status": RegressionStatus(result.regression_status)}
        )
        self.candidates.replace_all(
            [updated if item.asset_id == candidate.asset_id else item for item in self.candidates.all()]
        )
        return updated

    def _require_candidate(self, asset_id: str) -> AssetCandidate:
        candidate = self.candidates.get(asset_id)
        if candidate is None:
            raise KeyError(f"unknown asset_id: {asset_id}")
        return candidate

    def _validate_target(self, candidate: AssetCandidate, target: AssetStatus) -> None:
        correction = self.latest_correction(candidate.asset_id)
        reviews = self.current_reviews_for(candidate.asset_id) if correction else []
        roles = {review.review_role for review in reviews}
        if target == AssetStatus.AI_REVIEW_PENDING and not correction:
            raise ValueError("correction is required before AI review")
        if target in {AssetStatus.ADJUDICATION_PENDING, AssetStatus.QA_PENDING}:
            if not {"reviewer_a", "reviewer_b"}.issubset(roles):
                raise ValueError("independent reviewer_a and reviewer_b events are required")
        if target == AssetStatus.QA_PENDING:
            decisions = {review.review_role: review.decision for review in reviews}
            conflict = decisions.get("reviewer_a") != decisions.get("reviewer_b")
            if conflict and not self.current_adjudication_for(candidate.asset_id):
                raise ValueError("conflicting AI reviews require proposed adjudication")
        if target == AssetStatus.EXPERT_REVIEW_PENDING:
            check = self.current_quality_check_for(candidate.asset_id)
            if not check or not check.passed:
                raise ValueError("all QA checks must pass before expert review")
        if target == AssetStatus.ACCEPTED:
            if correction is None or not correction.corrected_answer.strip():
                raise ValueError("accepted requires a non-empty corrected answer")
            if not {"reviewer_a", "reviewer_b"}.issubset(roles):
                raise ValueError("accepted requires independent AI-A and AI-B reviews")
            decisions = {review.review_role: review.decision for review in reviews}
            if decisions.get("reviewer_a") != decisions.get("reviewer_b") and not self.current_adjudication_for(
                candidate.asset_id
            ):
                raise ValueError("accepted requires adjudication evidence for AI review conflict")
            final = [review for review in reviews if review.review_role == "final_expert"]
            if not final or final[-1].review_actor_type != "legal_expert" or final[-1].decision != "approve":
                raise ValueError("accepted requires explicit final legal expert approval")
            check = self.current_quality_check_for(candidate.asset_id)
            if not check or not check.passed:
                raise ValueError("accepted requires passed QA")
