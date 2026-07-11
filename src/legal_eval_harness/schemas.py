from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


VISIBLE_INPUT_FIELDS = [
    "sample_id",
    "source_dataset",
    "task_category",
    "user_question",
    "known_facts",
    "legal_concepts",
    "jurisdiction",
    "law_snapshot_date",
    "task_type",
    "legal_advice_boundary",
]

GOLD_LABEL_FIELDS = [
    "sample_id",
    "source_dataset",
    "task_category",
    "key_missing_facts",
    "expected_clarification_questions",
    "expected_answer_points",
    "risk_points",
    "expected_behavior",
    "rubric_items",
    "human_review_note",
]

SHARED_NON_GOLD_FIELDS = {"sample_id", "source_dataset", "task_category"}
PROTECTED_GOLD_FIELDS = set(GOLD_LABEL_FIELDS) - SHARED_NON_GOLD_FIELDS

SCORE_DIMENSIONS = [
    "missing_facts_awareness",
    "clarification_quality",
    "legal_grounding",
    "fact_rule_application",
    "conditional_reasoning",
    "risk_coverage",
    "overclaim_control",
    "hallucination_control",
    "data_tag_usability",
]

COARSE_ERROR_TAGS = [
    "missing_facts",
    "overclaim",
    "missing_evidence_warning",
    "unverified_basis",
    "fabricated_citation",
    "weak_fact_rule_application",
    "missing_procedure_warning",
    "jurisdiction_risk",
    "unsafe_action_suggestion",
    "needs_human_review",
]

DATA_ASSET_ROUTES = ["eval", "sft", "preference", "badcase", "regression"]
# Backward-compatible primary route values used by existing dashboards and artifacts.
# New code should use workflow_status, response_policy, and data_asset_routes.
DATA_ROUTES = [*DATA_ASSET_ROUTES, "human_review"]
WORKFLOW_STATUSES = ["pending_review", "reviewed", "blocked", "released"]
WORKFLOW_TRANSITIONS = {
    "pending_review": {"reviewed", "blocked", "released"},
    "reviewed": {"reviewed", "blocked", "released"},
    "blocked": {"blocked"},
    "released": {"released"},
}
RESPONSE_POLICIES = ["auto_answer", "grounded_answer", "clarify", "human_review", "block"]
# Deprecated alias retained for old routing artifacts. Group-level release gates use
# RELEASE_GATE_DECISIONS instead of overloading the same field name.
RELEASE_DECISIONS = RESPONSE_POLICIES
RELEASE_GATE_DECISIONS = ["candidate_auto_answer", "limited_release", "blocked"]
TASK_CATEGORIES = ["consultation", "case_analysis", "document_drafting"]


class EvalInputRow(BaseModel):
    sample_id: str
    source_dataset: str
    task_category: Literal["consultation", "case_analysis", "document_drafting"]
    user_question: str
    known_facts: str
    legal_concepts: str
    jurisdiction: str
    law_snapshot_date: str
    task_type: str
    legal_advice_boundary: str


class RubricItem(BaseModel):
    rubric_id: str
    rubric_dimension: str
    atomic_rubric_item: str
    max_score: int = 2
    scoring_rule_2: str = ""
    scoring_rule_1: str = ""
    scoring_rule_0: str = ""
    criticality: str = ""
    negative_rule: str = ""


class GoldLabelRow(BaseModel):
    sample_id: str
    source_dataset: str
    task_category: Literal["consultation", "case_analysis", "document_drafting"]
    key_missing_facts: str
    expected_clarification_questions: str
    expected_answer_points: str
    risk_points: str
    expected_behavior: str
    rubric_items: list[RubricItem] = Field(default_factory=list)
    human_review_note: str = ""


class ErrorTag(BaseModel):
    coarse_error_tag: Literal[
        "missing_facts",
        "overclaim",
        "missing_evidence_warning",
        "unverified_basis",
        "fabricated_citation",
        "weak_fact_rule_application",
        "missing_procedure_warning",
        "jurisdiction_risk",
        "unsafe_action_suggestion",
        "needs_human_review",
    ]
    error_subtype: str = ""


class AtomicScore(BaseModel):
    rubric_id: str
    atomic_rubric_item: str
    score: int
    max_score: int = 2
    rationale: str = ""


class JudgeScorePayload(BaseModel):
    dimension_scores: dict[str, int]
    atomic_scores: list[AtomicScore]
    total_score: int
    max_score: int
    score_rate: float
    error_tags: list[ErrorTag]
    risk_level: Literal["low", "medium", "high"]
    judge_reason: str
    judge_confidence: Literal["low", "medium", "high"]
    needs_human_review: bool


class RoutingDecision(BaseModel):
    sample_id: str
    run_id: str
    main_error_type: str
    error_tags: list[ErrorTag]
    risk_level: Literal["low", "medium", "high"]
    workflow_status: Literal["pending_review", "reviewed", "blocked", "released"]
    response_policy: Literal["auto_answer", "grounded_answer", "clarify", "human_review", "block"]
    # Deprecated compatibility alias for response_policy.
    release_decision: Literal["auto_answer", "grounded_answer", "clarify", "human_review", "block"]
    data_asset_routes: list[Literal["eval", "sft", "preference", "badcase", "regression"]]
    data_route: Literal["eval", "sft", "preference", "badcase", "regression", "human_review"]
    route_reason: str
    route_subtype: str = ""
    priority: Literal["P0", "P1", "P2"]
    candidate_for_reuse: bool
    requires_correction: bool
    gold_approved: bool
    # Deprecated compatibility alias for gold_approved.
    reusable_as_gold_sample: bool
