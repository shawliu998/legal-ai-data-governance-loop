from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from .asset_ai_review import _generate_json_with_retries
from .asset_schemas import Adjudication, ExpertApprovalBinding, ReviewEvent
from .asset_service import AssetService
from .llm_client import LLMClient
from .utils import safe_text, utc_now_iso


BLIND_PROTOCOL = "blind-v2"
BLIND_SNAPSHOT_FIELDS = {
    "case_id",
    "jurisdiction",
    "law_snapshot_date",
    "user_prompt",
    "critical_facts",
    "allowed_sources",
    "provided_context",
}


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _blind_payload(service: AssetService, asset_id: str) -> tuple[dict[str, Any], Any, Any]:
    candidate = service.candidates.get(asset_id)
    correction = service.latest_correction(asset_id)
    if candidate is None or correction is None:
        raise ValueError(f"candidate/correction missing for {asset_id}")
    snapshot = {
        key: candidate.source_snapshot[key]
        for key in sorted(BLIND_SNAPSHOT_FIELDS)
        if key in candidate.source_snapshot
    }
    forbidden = {"human_pass_fail", "human_notes", "expected_behavior", "expected_human_review"}
    if forbidden.intersection(snapshot):
        raise AssertionError("blind payload leaked prior labels")
    payload = {
        "asset_id": asset_id,
        "asset_type": candidate.asset_type.value,
        "case": snapshot,
        "correction": {
            "correction_id": correction.correction_id,
            "revision_number": correction.revision_number,
            "corrected_answer": correction.corrected_answer,
            "chosen_answer": correction.chosen_answer,
            "rejected_answer": correction.rejected_answer,
            "preference_reason": correction.preference_reason,
        },
        "regression_assertion": (
            service.assertion_for(asset_id).model_dump(mode="json")
            if service.assertion_for(asset_id)
            else None
        ),
    }
    return payload, candidate, correction


def run_blind_review_v2(
    service: AssetService,
    asset_id: str,
    role: str,
    *,
    client: LLMClient,
    model_config: dict[str, Any],
    raw_output_root: str | Path,
) -> ReviewEvent:
    if role not in {"reviewer_a", "reviewer_b"}:
        raise ValueError("blind review role must be reviewer_a or reviewer_b")
    existing_id = f"REV-{asset_id}-{role}-{BLIND_PROTOCOL}-01"
    existing = service.reviews.get(existing_id)
    if existing is not None:
        return existing
    payload, candidate, correction = _blind_payload(service, asset_id)
    focus = (
        "独立判断法律结论、关键事实覆盖、危险行动建议、回答策略与资产类型适配"
        if role == "reviewer_a"
        else "独立判断不支持主张、过度确定、引用支持、追问/转人工需要与发布适配"
    )
    prompt = f"""你是 {role}，执行法律数据资产 blind-v2 预审。
你看不到 router、既有人审标签、另一审核员结果、历史审核或最终决定。不得根据原始失败标签推断结论。
审核重点：{focus}。
只输出单个 JSON 对象：
{{"decision":"approve|rework|reject","findings":["..."],"response_policy":"auto_answer|grounded_answer|clarify|human_review|block","legal_conclusion_supported":true,"critical_facts_covered":true,"dangerous_action_advice":false,"unsupported_claims":[],"citation_support":"passed|failed|not_applicable","should_clarify":true,"should_human_review":true}}
待审资产：{json.dumps(payload, ensure_ascii=False, sort_keys=True)}
"""
    started = time.perf_counter()
    parsed, raw_output = _generate_json_with_retries(
        client=client,
        prompt=prompt,
        model_config=model_config,
        version=f"asset-{BLIND_PROTOCOL}-{role}",
        sample_id=asset_id,
    )
    elapsed = time.perf_counter() - started
    decision = safe_text(parsed.get("decision"))
    if decision not in {"approve", "rework", "reject"}:
        decision = "rework"
    policy = safe_text(parsed.get("response_policy"))
    if policy not in {"auto_answer", "grounded_answer", "clarify", "human_review", "block"}:
        policy = "human_review"
    citation = safe_text(parsed.get("citation_support"))
    if citation not in {"passed", "failed", "not_applicable"}:
        citation = "not_applicable"
    raw_path = Path(raw_output_root) / asset_id / f"{role}.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_record = {
        "asset_id": asset_id,
        "role": role,
        "protocol": BLIND_PROTOCOL,
        "model_identifier": str(model_config.get("alias") or model_config.get("model")),
        "prompt_hash": _hash(prompt),
        "output_hash": _hash(raw_output),
        "raw_output": raw_output,
        "created_at": utc_now_iso(),
    }
    raw_path.write_text(json.dumps(raw_record, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    event = ReviewEvent(
        event_id=existing_id,
        asset_id=asset_id,
        review_actor_type="ai_model",
        review_role=role,
        decision=decision,
        findings=[safe_text(item) for item in parsed.get("findings", [])],
        response_policy=policy,
        legal_conclusion_supported=parsed.get("legal_conclusion_supported"),
        critical_facts_covered=parsed.get("critical_facts_covered"),
        dangerous_action_advice=parsed.get("dangerous_action_advice"),
        unsupported_claims=[safe_text(item) for item in parsed.get("unsupported_claims", [])],
        citation_support=citation,
        should_clarify=bool(parsed.get("should_clarify", False)),
        should_human_review=bool(parsed.get("should_human_review", False)),
        prompt_version=f"asset-{BLIND_PROTOCOL}-{role}",
        model_identifier=raw_record["model_identifier"],
        context_isolation_id=f"CTX-{asset_id}-{role}-{BLIND_PROTOCOL}",
        input_hash=raw_record["prompt_hash"],
        output_hash=raw_record["output_hash"],
        review_elapsed_seconds=round(elapsed, 3),
        correction_id=correction.correction_id,
        correction_revision=correction.revision_number,
        source_snapshot_id=candidate.source_snapshot_id,
        corrected_answer_hash=_hash(correction.corrected_answer),
        review_protocol_version=BLIND_PROTOCOL,
        raw_output_path=str(raw_path),
        created_at=raw_record["created_at"],
    )
    service.reviews.append(event)
    return event


def adjudicate_blind_v2(
    service: AssetService,
    asset_id: str,
    *,
    client: LLMClient,
    model_config: dict[str, Any],
    raw_output_root: str | Path,
) -> Adjudication:
    event_id = f"ADJ-{asset_id}-{BLIND_PROTOCOL}-01"
    existing = service.adjudications.get(event_id)
    if existing is not None:
        return existing
    reviews = {
        row.review_role: row
        for row in service.reviews_for(asset_id)
        if row.review_protocol_version == BLIND_PROTOCOL
    }
    if not {"reviewer_a", "reviewer_b"}.issubset(reviews):
        raise ValueError(f"blind-v2 reviews missing for {asset_id}")
    a, b = reviews["reviewer_a"], reviews["reviewer_b"]
    fields = (
        "decision",
        "response_policy",
        "legal_conclusion_supported",
        "critical_facts_covered",
        "dangerous_action_advice",
        "citation_support",
        "should_clarify",
        "should_human_review",
    )
    conflicts = [field for field in fields if getattr(a, field) != getattr(b, field)]
    raw_path = Path(raw_output_root) / asset_id / "adjudicator.json"
    if conflicts:
        prompt = f"""仅归并两个 blind-v2 AI 预审的冲突，不得批准资产或参考任何人审标签。
只输出 JSON：{{"proposed_decision":"approve|rework|reject","rationale":"..."}}
冲突字段：{json.dumps(conflicts, ensure_ascii=False)}
Reviewer A：{a.model_dump_json()}
Reviewer B：{b.model_dump_json()}
"""
        parsed, raw_output = _generate_json_with_retries(
            client=client,
            prompt=prompt,
            model_config=model_config,
            version=f"asset-{BLIND_PROTOCOL}-adjudicator",
            sample_id=asset_id,
        )
        proposed = safe_text(parsed.get("proposed_decision"))
        if proposed not in {"approve", "rework", "reject"}:
            proposed = "rework"
        rationale = safe_text(parsed.get("rationale")) or "Blind reviewers conflict."
        status = "proposed_adjudication"
        model_identifier = str(model_config.get("alias") or model_config.get("model"))
        prompt_hash, output_hash = _hash(prompt), _hash(raw_output)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(
            json.dumps(
                {
                    "asset_id": asset_id,
                    "protocol": BLIND_PROTOCOL,
                    "model_identifier": model_identifier,
                    "prompt_hash": prompt_hash,
                    "output_hash": output_hash,
                    "raw_output": raw_output,
                    "created_at": utc_now_iso(),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    else:
        proposed, rationale, status = a.decision, "Blind reviewers agree on all tracked fields.", "not_required"
        model_identifier = "deterministic-conflict-detector-v2"
        prompt_hash = _hash(a.model_dump_json() + b.model_dump_json())
        output_hash = _hash(proposed)
        raw_path = Path("")
    result = Adjudication(
        adjudication_id=event_id,
        asset_id=asset_id,
        status=status,
        conflicts=conflicts,
        proposed_decision=proposed,
        rationale=rationale,
        model_identifier=model_identifier,
        prompt_version=f"asset-{BLIND_PROTOCOL}-adjudicator",
        input_hash=prompt_hash,
        output_hash=output_hash,
        correction_id=a.correction_id,
        correction_revision=a.correction_revision,
        source_snapshot_id=a.source_snapshot_id,
        corrected_answer_hash=a.corrected_answer_hash,
        review_protocol_version=BLIND_PROTOCOL,
        raw_output_path=str(raw_path) if conflicts else "",
        created_at=utc_now_iso(),
    )
    service.adjudications.append(result)
    return result


def backfill_lineage_and_expert_bindings(
    service: AssetService,
    *,
    review_round_dir: str | Path,
) -> tuple[int, int]:
    review_dir = Path(review_round_dir)
    files = sorted(review_dir.glob("*.csv"))
    accepted_rows: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in files:
        frame = pd.read_csv(path).fillna("")
        for row in frame.to_dict(orient="records"):
            asset_id = safe_text(row.get("asset_id"))
            snapshot_text = safe_text(row.get("source_snapshot"))
            snapshot_id = safe_text(row.get("source_snapshot_id"))
            if snapshot_text and snapshot_id:
                try:
                    snapshot = json.loads(snapshot_text)
                except json.JSONDecodeError:
                    snapshot = {}
                if snapshot:
                    service.register_source_snapshot(
                        asset_id=asset_id,
                        source_snapshot_id=snapshot_id,
                        source_snapshot=snapshot,
                        evidence_source=str(path),
                        reconstructed=True,
                        created_at=utc_now_iso(),
                    )
            if safe_text(row.get("expert_decision")) == "accepted":
                accepted_rows[asset_id] = (path, row)
    for candidate in service.candidates.all():
        service.register_source_snapshot(
            asset_id=candidate.asset_id,
            source_snapshot_id=candidate.source_snapshot_id,
            source_snapshot=candidate.source_snapshot,
            evidence_source="current_candidate_state",
            reconstructed=True,
        )
    binding_count = 0
    final_event_updates: dict[str, ReviewEvent] = {}
    for candidate in service.candidates.all():
        if candidate.asset_status.value != "accepted":
            continue
        if candidate.asset_id not in accepted_rows:
            raise ValueError(f"no accepted expert submission for {candidate.asset_id}")
        path, row = accepted_rows[candidate.asset_id]
        submitted_answer = safe_text(row.get("corrected_answer")).strip()
        matches = [
            correction
            for correction in service.corrections.all()
            if correction.asset_id == candidate.asset_id
            and correction.corrected_answer.strip() == submitted_answer
        ]
        if not matches:
            raise ValueError(f"expert submission text does not match a correction: {candidate.asset_id}")
        correction = max(matches, key=lambda item: item.revision_number)
        reason = safe_text(row.get("expert_override_reason")).strip()
        final_events = [
            event
            for event in service.reviews_for(candidate.asset_id)
            if event.review_role == "final_expert"
            and event.decision == "approve"
            and reason in event.findings
        ]
        if not final_events:
            raise ValueError(f"accepted submission has no matching expert event: {candidate.asset_id}")
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        binding_id = f"EAB-{candidate.asset_id}-{correction.revision_number:02d}"
        existing_binding = service.expert_approval_bindings.get(binding_id)
        binding = existing_binding or ExpertApprovalBinding(
            binding_id=binding_id,
            asset_id=candidate.asset_id,
            correction_id=correction.correction_id,
            correction_revision=correction.revision_number,
            source_snapshot_id=safe_text(row.get("source_snapshot_id")) or candidate.source_snapshot_id,
            corrected_answer_hash=_hash(correction.corrected_answer),
            expert_decision="accepted",
            original_review_event_id=final_events[-1].event_id,
            submission_file=str(path),
            submission_file_sha256=file_hash,
            reconstruction_method="matched_submitted_text_and_reason",
            created_at=utc_now_iso(),
        )
        if existing_binding is not None and (
            binding.correction_id != correction.correction_id
            or binding.source_snapshot_id
            != (safe_text(row.get("source_snapshot_id")) or candidate.source_snapshot_id)
            or binding.corrected_answer_hash != _hash(correction.corrected_answer)
        ):
            raise ValueError(f"existing expert binding conflicts with current correction: {candidate.asset_id}")
        if existing_binding is None and service.expert_approval_bindings.append(binding):
            binding_count += 1
        final_event = final_events[-1]
        final_event_updates[final_event.event_id] = final_event.model_copy(
            update={
                "correction_id": correction.correction_id,
                "correction_revision": correction.revision_number,
                "source_snapshot_id": binding.source_snapshot_id,
                "corrected_answer_hash": binding.corrected_answer_hash,
            }
        )
    if final_event_updates:
        service.reviews.replace_all(
            [final_event_updates.get(row.event_id, row) for row in service.reviews.all()]
        )
    from .asset_quality import run_asset_qa

    for candidate in service.candidates.all():
        if candidate.asset_status.value != "accepted":
            continue
        if service.current_quality_check_for(candidate.asset_id) is None:
            check = run_asset_qa(
                service, candidate.asset_id, transition_after_check=False
            )
            if not check.passed:
                raise ValueError(f"current-correction QA failed during lineage backfill: {candidate.asset_id}")
    return len(service.source_snapshot_versions.all()), binding_count
