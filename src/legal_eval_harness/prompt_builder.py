from __future__ import annotations

from pathlib import Path
from typing import Any

from .schemas import PROTECTED_GOLD_FIELDS, VISIBLE_INPUT_FIELDS
from .utils import json_dumps, safe_text


PROMPT_FILES = {
    "V0": "v0_direct_answer.txt",
    "V1": "v1_answer_protocol.txt",
    "V2": "v2_blind_review_agent.txt",
    "V3": "v3_workflow_agent.txt",
    "V4": "v4_grounded_answer.txt",
    "V5": "v5_clarification_first.txt",
    "JUDGE": "judge_consultation.txt",
    "JUDGE_CONSULTATION": "judge_consultation.txt",
    "JUDGE_CASE_ANALYSIS": "judge_case_analysis.txt",
    "JUDGE_DOCUMENT_DRAFTING": "judge_document_drafting.txt",
}

JUDGE_PROMPT_BY_CATEGORY = {
    "consultation": "JUDGE_CONSULTATION",
    "case_analysis": "JUDGE_CASE_ANALYSIS",
    "document_drafting": "JUDGE_DOCUMENT_DRAFTING",
}


class PromptBuilder:
    def __init__(self, prompt_dir: str | Path = "prompts") -> None:
        self.prompt_dir = Path(prompt_dir)

    def load_template(self, prompt_id: str) -> str:
        if prompt_id not in PROMPT_FILES:
            raise ValueError(f"Unknown prompt_id: {prompt_id}")
        path = self.prompt_dir / PROMPT_FILES[prompt_id]
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8")

    def render_agent_prompt(
        self,
        version: str,
        eval_row: dict[str, Any],
        *,
        v0_output: str = "",
    ) -> tuple[str, list[str]]:
        if version not in {"V0", "V1", "V2", "V3", "V4", "V5"}:
            raise ValueError(f"Unsupported agent version: {version}")
        protected_present = PROTECTED_GOLD_FIELDS.intersection(eval_row.keys())
        if protected_present:
            raise ValueError(f"Agent prompt received protected gold fields: {sorted(protected_present)}")

        visible_context = {field: safe_text(eval_row.get(field, "")) for field in VISIBLE_INPUT_FIELDS}
        if version == "V2":
            visible_context["v0_output"] = safe_text(v0_output)
        template = self.load_template(version)
        prompt = template.format(**visible_context)
        self.assert_no_gold_placeholders(prompt, version)
        visible_fields = list(VISIBLE_INPUT_FIELDS)
        if version == "V2":
            visible_fields.append("V0_output")
        return prompt, visible_fields

    def render_judge_prompt(
        self,
        *,
        eval_row: dict[str, Any],
        gold_row: dict[str, Any],
        model_output: str,
        run_id: str,
        version: str,
    ) -> tuple[str, str]:
        task_category = safe_text(eval_row.get("task_category", "consultation")) or "consultation"
        prompt_id = JUDGE_PROMPT_BY_CATEGORY.get(task_category, "JUDGE_CONSULTATION")
        template = self.load_template(prompt_id)
        values = {field: safe_text(eval_row.get(field, "")) for field in VISIBLE_INPUT_FIELDS}
        values.update(
            {
                "run_id": run_id,
                "version": version,
                "task_category": task_category,
                "model_output": safe_text(model_output)[:3000],
                "key_missing_facts": safe_text(gold_row.get("key_missing_facts", "")),
                "expected_clarification_questions": safe_text(
                    gold_row.get("expected_clarification_questions", "")
                ),
                "expected_answer_points": safe_text(gold_row.get("expected_answer_points", "")),
                "risk_points": safe_text(gold_row.get("risk_points", "")),
                "expected_behavior": safe_text(gold_row.get("expected_behavior", "")),
                "rubric_items": safe_text(gold_row.get("rubric_items", "[]")),
                "human_review_note": safe_text(gold_row.get("human_review_note", "")),
                "score_dimensions": json_dumps(
                    [
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
                ),
            }
        )
        return template.format(**values), prompt_id

    @staticmethod
    def assert_no_gold_placeholders(prompt: str, version: str) -> None:
        forbidden_tokens = [
            "{key_missing_facts}",
            "{risk_points}",
            "{expected_answer_points}",
            "{expected_clarification_questions}",
            "{expected_behavior}",
            "{rubric_items}",
        ]
        found = [token for token in forbidden_tokens if token in prompt]
        if found:
            raise ValueError(f"{version} prompt still contains gold placeholders: {found}")
