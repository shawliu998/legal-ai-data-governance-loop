from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class AssetType(StrEnum):
    SFT = "sft"
    PREFERENCE = "preference"
    REGRESSION = "regression"


class AssetStatus(StrEnum):
    PROPOSED = "proposed"
    CORRECTION_DRAFTING = "correction_drafting"
    AI_REVIEW_PENDING = "ai_review_pending"
    ADJUDICATION_PENDING = "adjudication_pending"
    QA_PENDING = "qa_pending"
    EXPERT_REVIEW_PENDING = "expert_review_pending"
    ACCEPTED = "accepted"
    REWORK_REQUIRED = "rework_required"
    REJECTED = "rejected"


class DatasetMembershipStatus(StrEnum):
    NOT_VERSIONED = "not_versioned"
    INCLUDED = "included"
    DEPRECATED = "deprecated"


class RegressionStatus(StrEnum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"


class AssetCandidate(BaseModel):
    asset_id: str
    source_case_id: str
    source_run_id: str
    asset_type: AssetType
    failure_type: str
    proposed_response_policy: Literal[
        "auto_answer", "grounded_answer", "clarify", "human_review", "block"
    ]
    source_snapshot_id: str
    source_snapshot: dict[str, Any] = Field(default_factory=dict)
    training_eligible: bool
    public_visibility: Literal["public_redacted", "restricted"] = "restricted"
    asset_status: AssetStatus = AssetStatus.PROPOSED
    dataset_membership_status: DatasetMembershipStatus = DatasetMembershipStatus.NOT_VERSIONED
    regression_status: RegressionStatus = RegressionStatus.NOT_RUN
    created_at: str

    @model_validator(mode="after")
    def validate_training_eligibility(self) -> "AssetCandidate":
        if self.asset_type == AssetType.REGRESSION and self.training_eligible:
            raise ValueError("regression/eval assets cannot be training eligible")
        return self


class Correction(BaseModel):
    correction_id: str
    asset_id: str
    revision_number: int = Field(ge=1)
    corrected_answer: str
    chosen_answer: str = ""
    rejected_answer: str = ""
    preference_reason: str = ""
    author_type: Literal["ai_model", "legal_expert"]
    prompt_version: str
    model_identifier: str
    created_at: str

    @model_validator(mode="after")
    def validate_preference_pair(self) -> "Correction":
        if bool(self.chosen_answer) != bool(self.rejected_answer):
            raise ValueError("chosen_answer and rejected_answer must be supplied together")
        if self.chosen_answer and self.chosen_answer.strip() == self.rejected_answer.strip():
            raise ValueError("preference chosen and rejected answers must differ")
        return self


class ReviewEvent(BaseModel):
    event_id: str
    asset_id: str
    review_actor_type: Literal["ai_model", "legal_expert"]
    review_role: Literal["reviewer_a", "reviewer_b", "ai_adjudicator", "final_expert"]
    decision: Literal["approve", "rework", "reject"]
    findings: list[str] = Field(default_factory=list)
    response_policy: Literal[
        "auto_answer", "grounded_answer", "clarify", "human_review", "block"
    ]
    legal_conclusion_supported: bool | None = None
    critical_facts_covered: bool | None = None
    dangerous_action_advice: bool | None = None
    unsupported_claims: list[str] = Field(default_factory=list)
    citation_support: Literal["passed", "failed", "not_applicable"] = "not_applicable"
    should_clarify: bool = False
    should_human_review: bool = False
    prompt_version: str
    model_identifier: str
    context_isolation_id: str
    input_hash: str
    output_hash: str
    review_elapsed_seconds: float = Field(ge=0)
    expert_override: bool | None = None
    expert_override_reason: str = ""
    correction_id: str = ""
    correction_revision: int = 0
    source_snapshot_id: str = ""
    corrected_answer_hash: str = ""
    review_protocol_version: str = "legacy-v1"
    raw_output_path: str = ""
    created_at: str


class Adjudication(BaseModel):
    adjudication_id: str
    asset_id: str
    status: Literal["not_required", "proposed_adjudication"]
    conflicts: list[str] = Field(default_factory=list)
    proposed_decision: Literal["approve", "rework", "reject"]
    rationale: str
    model_identifier: str
    prompt_version: str
    input_hash: str
    output_hash: str
    correction_id: str = ""
    correction_revision: int = 0
    source_snapshot_id: str = ""
    corrected_answer_hash: str = ""
    review_protocol_version: str = "legacy-v1"
    raw_output_path: str = ""
    created_at: str


class SourceSnapshotVersion(BaseModel):
    snapshot_version_id: str
    asset_id: str
    source_snapshot_id: str
    version_number: int = Field(ge=1)
    source_snapshot_hash: str
    source_snapshot: dict[str, Any]
    evidence_source: str
    reconstructed: bool = False
    created_at: str


class ExpertApprovalBinding(BaseModel):
    binding_id: str
    asset_id: str
    correction_id: str
    correction_revision: int = Field(ge=1)
    source_snapshot_id: str
    corrected_answer_hash: str
    expert_decision: Literal["accepted"]
    original_review_event_id: str
    submission_file: str
    submission_file_sha256: str
    reviewer_role: Literal["legal_phd"] = "legal_phd"
    reconstruction_method: Literal["matched_submitted_text_and_reason"]
    created_at: str


class QualityCheck(BaseModel):
    quality_check_id: str
    asset_id: str
    pii_check: Literal["passed", "failed"]
    duplicate_check: Literal["passed", "failed"]
    source_traceability: Literal["passed", "failed"]
    contamination_check: Literal["passed", "failed", "not_applicable"]
    law_effective_date_check: Literal["passed", "failed"]
    type_specific_check: Literal["passed", "failed"]
    correction_id: str = ""
    correction_revision: int = 0
    source_snapshot_id: str = ""
    corrected_answer_hash: str = ""
    findings: list[str] = Field(default_factory=list)
    created_at: str

    @property
    def passed(self) -> bool:
        return all(
            value == "passed"
            for value in (
                self.pii_check,
                self.duplicate_check,
                self.source_traceability,
                self.law_effective_date_check,
                self.type_specific_check,
            )
        ) and self.contamination_check != "failed"


class RegressionAssertion(BaseModel):
    assertion_id: str
    asset_id: str
    expected_response_policy: list[
        Literal["auto_answer", "grounded_answer", "clarify", "human_review", "block"]
    ]
    forbidden_claims: list[str] = Field(default_factory=list)
    required_topics: list[str] = Field(default_factory=list)
    required_topic_aliases: dict[str, list[str]] = Field(default_factory=dict)
    citation_required: bool = False
    revision_number: int = Field(default=1, ge=1)
    created_at: str

    @model_validator(mode="after")
    def validate_nonempty(self) -> "RegressionAssertion":
        if not (self.expected_response_policy or self.forbidden_claims or self.required_topics):
            raise ValueError("regression assertion must contain at least one condition")
        return self


class DatasetMembership(BaseModel):
    dataset_membership_id: str = ""
    asset_id: str
    dataset_release_id: str
    split: Literal["train", "validation", "test", "bug_reproduction"]
    status: DatasetMembershipStatus = DatasetMembershipStatus.INCLUDED
    created_at: str

    @model_validator(mode="after")
    def populate_membership_id(self) -> "DatasetMembership":
        if not self.dataset_membership_id:
            self.dataset_membership_id = (
                f"MEM-{self.dataset_release_id}-{self.asset_id}-{self.split}"
            )
        return self


class DatasetRelease(BaseModel):
    dataset_release_id: str
    version: str
    asset_ids: list[str]
    created_at: str
    git_commit: str
    known_limitations: list[str] = Field(default_factory=list)


class RegressionResult(BaseModel):
    regression_id: str
    asset_id: str
    baseline_run_id: str
    rerun_id: str
    model_alias: str
    prompt_version: str
    assertion_results: dict[str, bool]
    regression_status: Literal["passed", "failed"]
    failure_reason: str = ""
    output_text_hash: str
    rerun_attempt_number: int = 0
    scoring_revision: str = "legacy-v1"
    source_regression_id: str = ""
    created_at: str


class StateTransitionEvent(BaseModel):
    event_id: str
    asset_id: str
    from_status: AssetStatus
    to_status: AssetStatus
    reason: str
    actor_type: Literal["system", "qa_system", "ai_model", "legal_expert"]
    created_at: str
