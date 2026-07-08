from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from .io_excel import DatasetBundle, find_gold_row
from .utils import json_dumps, json_loads_or_none, safe_text


BRACKETED_SOURCE_ID_RE = re.compile(r"\[([A-Z][A-Z0-9_-]{2,})\]")
BARE_SOURCE_ID_RE = re.compile(r"(?<![A-Z0-9_-])([A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+)(?![A-Z0-9_-])")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    text = safe_text(text).lower()
    words = WORD_RE.findall(text)
    cjk = [ch for ch in text if CJK_RE.match(ch)]
    cjk_bigrams = [cjk[idx] + cjk[idx + 1] for idx in range(len(cjk) - 1)]
    return words + cjk + cjk_bigrams


def _content_tokens(text: str) -> set[str]:
    stop_chars = set("的一是在了和与及或但若如可应需能不能是否进行根据依据对于关于")
    return {token for token in _tokenize(text) if len(token) > 1 and token not in stop_chars}


def _parse_source_ids(text: str) -> list[str]:
    text = safe_text(text)
    return sorted(set(BRACKETED_SOURCE_ID_RE.findall(text) + BARE_SOURCE_ID_RE.findall(text)))


def _expected_source_ids(gold_row: dict[str, Any]) -> list[str]:
    return _parse_source_ids(gold_row.get("expected_answer_points", ""))


def _score_bm25(query_tokens: list[str], doc_tokens: list[str], idf: dict[str, float], avgdl: float) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    counts = Counter(doc_tokens)
    doc_len = len(doc_tokens)
    k1 = 1.5
    b = 0.75
    score = 0.0
    for token in set(query_tokens):
        if token not in counts:
            continue
        tf = counts[token]
        denom = tf + k1 * (1 - b + b * doc_len / max(avgdl, 1.0))
        score += idf.get(token, 0.0) * (tf * (k1 + 1) / denom)
    return round(score, 6)


def _metadata_boost(query: str, row: dict[str, Any]) -> float:
    query_text = safe_text(query).lower()
    tags = [tag for tag in re.split(r"[;；,\s]+", safe_text(row.get("tags")).lower()) if tag]
    source_type = safe_text(row.get("source_type"))
    boost = 0.0
    boost += 0.12 * sum(1 for tag in tags if tag and tag in query_text)
    if safe_text(row.get("source_id")).lower() in query_text:
        boost += 2.0
    if source_type in {"contract_clause", "policy_clause", "evidence_excerpt"} and "仅根据" in query:
        boost += 0.25
    if source_type == "statute_article" and any(term in query for term in ["法条", "民法典", "劳动合同法"]):
        boost += 0.25
    if source_type == "case_summary" and any(term in query for term in ["案例", "裁判", "法院"]):
        boost += 0.2
    return round(boost, 6)


def load_rag_corpus(path: str | Path) -> pd.DataFrame:
    corpus_path = Path(path)
    if not corpus_path.exists():
        raise FileNotFoundError(f"RAG corpus not found: {corpus_path}")
    corpus = pd.read_csv(corpus_path).fillna("")
    required = {"source_id", "title", "source_type", "jurisdiction", "text"}
    missing = sorted(required - set(corpus.columns))
    if missing:
        raise ValueError(f"RAG corpus missing required columns: {missing}")
    corpus["source_id"] = corpus["source_id"].map(safe_text)
    corpus["text"] = corpus["text"].map(safe_text)
    if corpus["source_id"].duplicated().any():
        duplicated = sorted(corpus.loc[corpus["source_id"].duplicated(), "source_id"].unique())
        raise ValueError(f"RAG corpus contains duplicate source_id values: {duplicated}")
    return corpus


def retrieve_contexts(
    *,
    eval_row: dict[str, Any],
    corpus: pd.DataFrame,
    top_k: int = 4,
    min_score: float = 0.0,
) -> list[dict[str, Any]]:
    query = " ".join(
        [
            safe_text(eval_row.get("user_question")),
            safe_text(eval_row.get("known_facts")),
            safe_text(eval_row.get("legal_concepts")),
            safe_text(eval_row.get("task_type")),
        ]
    )
    query_tokens = _tokenize(query)
    docs = []
    for _, row in corpus.iterrows():
        doc_text = " ".join(
            [
                safe_text(row.get("source_id")),
                safe_text(row.get("title")),
                safe_text(row.get("source_type")),
                safe_text(row.get("text")),
                safe_text(row.get("tags")),
            ]
        )
        docs.append((row.to_dict(), _tokenize(doc_text)))
    avgdl = sum(len(tokens) for _, tokens in docs) / max(len(docs), 1)
    doc_freq: Counter[str] = Counter()
    for _, tokens in docs:
        doc_freq.update(set(tokens))
    idf = {
        token: math.log(1 + (len(docs) - freq + 0.5) / (freq + 0.5))
        for token, freq in doc_freq.items()
    }

    scored = []
    for row, tokens in docs:
        bm25_score = _score_bm25(query_tokens, tokens, idf, avgdl)
        metadata_boost = _metadata_boost(query, row)
        final_score = round(bm25_score + metadata_boost, 6)
        if final_score >= min_score:
            row = dict(row)
            row["bm25_score"] = bm25_score
            row["metadata_boost"] = metadata_boost
            scored.append((final_score, row))
    scored.sort(key=lambda item: (-item[0], safe_text(item[1].get("source_id"))))
    return [dict(row, retrieval_score=score) for score, row in scored[:top_k]]


def format_retrieved_context(contexts: list[dict[str, Any]]) -> str:
    if not contexts:
        return "RAG 检索未命中可用来源；不得编造引用。"
    lines = ["RAG 检索上下文（仅可引用以下 source_id）："]
    for item in contexts:
        source_id = safe_text(item.get("source_id"))
        title = safe_text(item.get("title"))
        source_type = safe_text(item.get("source_type"))
        text = safe_text(item.get("text"))
        lines.append(f"[{source_id}] {title}｜{source_type}｜{text}")
    return "\n".join(lines)


def inject_retrieved_context(eval_row: dict[str, Any], contexts: list[dict[str, Any]]) -> dict[str, Any]:
    row = dict(eval_row)
    existing = safe_text(row.get("known_facts"))
    row["known_facts"] = existing + "\n\n" + format_retrieved_context(contexts)
    return row


def build_retrieval_log_row(
    *,
    run_row: dict[str, Any],
    contexts: list[dict[str, Any]],
    bundle: DatasetBundle,
) -> dict[str, Any]:
    gold_row = find_gold_row(bundle, safe_text(run_row["sample_id"]))
    retrieved_ids = [safe_text(item.get("source_id")) for item in contexts]
    expected_ids = _expected_source_ids(gold_row)
    expected_set = set(expected_ids)
    retrieved_set = set(retrieved_ids)
    hit_count = len(expected_set.intersection(retrieved_set))
    return {
        "run_id": run_row["run_id"],
        "sample_id": safe_text(run_row["sample_id"]),
        "model_alias": safe_text(run_row.get("model_alias")),
        "version": safe_text(run_row.get("version")),
        "workflow_condition": safe_text(run_row.get("workflow_condition")),
        "retrieved_source_ids": json_dumps(retrieved_ids),
        "retrieval_scores": json_dumps(
            {safe_text(item.get("source_id")): item.get("retrieval_score") for item in contexts}
        ),
        "expected_source_ids": json_dumps(expected_ids),
        "expected_source_hit_count": hit_count,
        "context_recall": round(hit_count / len(expected_set), 3) if expected_set else "",
        "context_precision": round(hit_count / len(retrieved_set), 3) if expected_set and retrieved_set else "",
        "retrieval_status": "hit" if contexts else "miss",
    }


def build_context_rows(*, run_row: dict[str, Any], contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for rank, item in enumerate(contexts, start=1):
        rows.append(
            {
                "run_id": run_row["run_id"],
                "sample_id": safe_text(run_row["sample_id"]),
                "model_alias": safe_text(run_row.get("model_alias")),
                "version": safe_text(run_row.get("version")),
                "rank": rank,
                "source_id": safe_text(item.get("source_id")),
                "source_type": safe_text(item.get("source_type")),
                "title": safe_text(item.get("title")),
                "retrieval_score": item.get("retrieval_score", 0.0),
                "bm25_score": item.get("bm25_score", 0.0),
                "metadata_boost": item.get("metadata_boost", 0.0),
                "authority_level": safe_text(item.get("authority_level")),
                "source_url": safe_text(item.get("source_url")),
                "text": safe_text(item.get("text")),
            }
        )
    return rows


def split_claims(output_text: str) -> list[str]:
    def collect_strings(value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            values: list[str] = []
            for item in value:
                values.extend(collect_strings(item))
            return values
        if isinstance(value, dict):
            values = []
            for item in value.values():
                values.extend(collect_strings(item))
            return values
        return []

    parsed = json_loads_or_none(output_text)
    raw_parts = collect_strings(parsed) if parsed is not None else [safe_text(output_text)]
    parts: list[str] = []
    for raw in raw_parts:
        parts.extend(re.split(r"[\n。；;!?！？]+", safe_text(raw)))
    return [part.strip(" -0123456789.、:：") for part in parts if len(part.strip()) >= 8]


def _claim_support_score(claim: str, source_text: str) -> float:
    claim_tokens = _content_tokens(claim)
    source_tokens = _content_tokens(source_text)
    if not claim_tokens or not source_tokens:
        return 0.0
    return round(len(claim_tokens.intersection(source_tokens)) / len(claim_tokens), 3)


def _is_risk_control_statement(claim: str) -> bool:
    text = safe_text(claim)
    markers = [
        "先确认",
        "不能编造",
        "不得编造",
        "需要补充",
        "需补充",
        "补充证据",
        "风险",
        "人审",
        "人工复核",
        "证据不足",
        "证据链不足",
        "依据不足",
        "条件化",
        "不能把",
        "只能引用",
        "可使用的依据",
        "检索命中",
        "若检索材料",
        "避免承诺",
    ]
    return any(marker in text for marker in markers)


def _is_reviewable_legal_claim(claim: str) -> bool:
    text = safe_text(claim)
    if _is_risk_control_statement(text):
        return False
    markers = [
        "一定",
        "必须",
        "构成",
        "承担",
        "解除",
        "赔偿",
        "违法",
        "有效",
        "无效",
        "责任",
        "退费",
        "退款",
        "删除",
        "担保",
        "保证",
        "劳动关系",
        "可以要求",
        "可给予",
        "可主张",
        "可解除",
        "可要求",
        "不能主张",
        "不能排除",
        "不当然",
    ]
    return any(marker in text for marker in markers)


def verify_claims(output_text: str, contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    context_by_id = {safe_text(item.get("source_id")): safe_text(item.get("text")) for item in contexts}
    all_context_text = "\n".join(context_by_id.values())
    checks: list[dict[str, Any]] = []
    for claim in split_claims(output_text):
        reviewable = _is_reviewable_legal_claim(claim)
        cited_ids = _parse_source_ids(claim)
        candidate_ids = cited_ids or list(context_by_id)
        scores = {
            source_id: _claim_support_score(claim, context_by_id.get(source_id, ""))
            for source_id in candidate_ids
        }
        best_source_id = max(scores, key=scores.get) if scores else ""
        best_score = scores.get(best_source_id, _claim_support_score(claim, all_context_text))
        if cited_ids and any(source_id not in context_by_id for source_id in cited_ids):
            label = "fabricated_citation"
        elif not reviewable:
            label = "risk_control_or_nonlegal_statement"
        elif best_score >= 0.35:
            label = "supported"
        elif cited_ids:
            label = "weak_or_unsupported_cited_claim"
        else:
            label = "uncited_or_unsupported_claim"
        checks.append(
            {
                "claim": claim,
                "cited_source_ids": cited_ids,
                "best_source_id": best_source_id,
                "support_score": best_score,
                "support_label": label,
                "reviewable_legal_claim": reviewable,
            }
        )
    return checks


def _has_contradiction_signal(claim: str, source_text: str) -> bool:
    claim_text = safe_text(claim)
    source = safe_text(source_text)
    if not claim_text or not source:
        return False
    limitation_markers = [
        "需另行证明",
        "需要另行证明",
        "不等于",
        "不能直接",
        "并非自动",
        "必须额外证明",
        "不构成法律咨询",
        "不构成最终法律意见",
        "若",
    ]
    if any(marker in claim_text for marker in limitation_markers):
        return False
    positive_claim = any(
        marker in claim_text
        for marker in ["可以", "应当", "直接要求", "直接认定", "构成", "属于", "可主张", "可要求", "具备主张"]
    )
    negative_source = any(marker in source for marker in ["不得", "不能", "不支持", "未规定", "需另行证明", "不足以", "未显示"])
    return positive_claim and negative_source


def _entailment_product_action(label: str) -> str:
    if label == "supported":
        return "pass_citation_gate"
    if label == "partially_supported":
        return "human_review_or_revision"
    if label == "unsupported":
        return "badcase_and_regression_eval"
    if label == "contradicted":
        return "release_blocker"
    if label == "no_citation":
        return "human_review_and_prompt_fix"
    if label == "out_of_scope_source":
        return "source_boundary_regression"
    if label == "fabricated_citation":
        return "release_blocker_and_badcase"
    return "not_applicable"


def _entailment_reason(label: str, *, best_score: float, out_of_scope: list[str], fabricated: list[str]) -> str:
    if label == "fabricated_citation":
        return f"cited source IDs are not available in provided or retrieved context: {fabricated}"
    if label == "out_of_scope_source":
        return f"claim cites source IDs outside the allowed source boundary: {out_of_scope}"
    if label == "no_citation":
        return "reviewable legal claim has no explicit citation"
    if label == "contradicted":
        return "source text contains lexical contradiction or limitation signals against the claim"
    if label == "supported":
        return f"best lexical support score {best_score:.3f} meets supported threshold"
    if label == "partially_supported":
        return f"best lexical support score {best_score:.3f} is partial and needs legal review"
    if label == "unsupported":
        return f"best lexical support score {best_score:.3f} is below support threshold"
    return "non-reviewable risk-control, procedural, or nonlegal statement"


def build_claim_entailment_rows(
    *,
    run_row: dict[str, Any],
    contexts: list[dict[str, Any]],
    output_text: str,
    allowed_source_ids: list[str] | None = None,
    provided_contexts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build one row per extracted claim for citation entailment triage.

    This is a deterministic triage layer. It does not replace legal review; it
    creates a claim/source/action table that reviewers can audit.
    """
    allowed_set = {safe_text(source_id) for source_id in (allowed_source_ids or []) if safe_text(source_id)}
    source_rows: dict[str, dict[str, Any]] = {}
    for source in contexts:
        source_id = safe_text(source.get("source_id"))
        if source_id:
            source_rows[source_id] = dict(source, source_origin=safe_text(source.get("source_origin")) or "retrieved")
    for source in provided_contexts or []:
        source_id = safe_text(source.get("source_id"))
        if source_id and source_id not in source_rows:
            source_rows[source_id] = {
                "source_id": source_id,
                "text": safe_text(source.get("text")),
                "source_type": safe_text(source.get("source_type")) or "provided_context",
                "title": safe_text(source.get("title")) or source_id,
                "source_origin": "provided_context",
            }

    available_ids = set(source_rows)
    all_source_text = "\n".join(safe_text(source.get("text")) for source in source_rows.values())
    rows: list[dict[str, Any]] = []
    for claim_index, claim in enumerate(split_claims(output_text), start=1):
        reviewable = _is_reviewable_legal_claim(claim)
        cited_ids = _parse_source_ids(claim)
        fabricated = sorted([source_id for source_id in cited_ids if source_id not in available_ids])
        out_of_scope = sorted([source_id for source_id in cited_ids if allowed_set and source_id not in allowed_set])
        checked_ids = cited_ids or sorted(available_ids)
        scores = {
            source_id: _claim_support_score(claim, safe_text(source_rows.get(source_id, {}).get("text")))
            for source_id in checked_ids
            if source_id in source_rows
        }
        best_source_id = max(scores, key=scores.get) if scores else ""
        best_score = scores.get(best_source_id, _claim_support_score(claim, all_source_text))
        best_source_text = safe_text(source_rows.get(best_source_id, {}).get("text"))
        if fabricated:
            label = "fabricated_citation"
        elif out_of_scope:
            label = "out_of_scope_source"
        elif not reviewable:
            label = "not_reviewable"
        elif not cited_ids:
            label = "no_citation"
        elif best_source_id and _has_contradiction_signal(claim, best_source_text):
            label = "contradicted"
        elif best_score >= 0.45:
            label = "supported"
        elif best_score >= 0.25:
            label = "partially_supported"
        else:
            label = "unsupported"
        rows.append(
            {
                "run_id": run_row["run_id"],
                "sample_id": safe_text(run_row.get("sample_id")),
                "model_alias": safe_text(run_row.get("model_alias")),
                "version": safe_text(run_row.get("version")),
                "workflow_condition": safe_text(run_row.get("workflow_condition")),
                "claim_index": claim_index,
                "claim": claim,
                "reviewable_legal_claim": reviewable,
                "cited_source_ids": json_dumps(cited_ids),
                "checked_source_ids": json_dumps(checked_ids),
                "allowed_source_ids": json_dumps(sorted(allowed_set)),
                "fabricated_source_ids": json_dumps(fabricated),
                "out_of_scope_source_ids": json_dumps(out_of_scope),
                "best_source_id": best_source_id,
                "best_source_type": safe_text(source_rows.get(best_source_id, {}).get("source_type")),
                "best_source_origin": safe_text(source_rows.get(best_source_id, {}).get("source_origin")),
                "support_score": best_score,
                "entailment_label": label,
                "product_action": _entailment_product_action(label),
                "entailment_reason": _entailment_reason(
                    label, best_score=best_score, out_of_scope=out_of_scope, fabricated=fabricated
                ),
            }
        )
    return rows


def summarize_claim_entailment(rows: pd.DataFrame, output_path: str | Path) -> pd.DataFrame:
    if rows.empty:
        result = pd.DataFrame(
            [
                {
                    "total_claim_rows": 0,
                    "reviewable_claim_rows": 0,
                    "citation_gate_issue_rows": 0,
                    "release_blocker_rows": 0,
                }
            ]
        )
    else:
        issue_labels = {
            "unsupported",
            "contradicted",
            "no_citation",
            "out_of_scope_source",
            "fabricated_citation",
        }
        release_blockers = {"contradicted", "fabricated_citation", "out_of_scope_source"}
        result = pd.DataFrame(
            [
                {
                    "total_claim_rows": len(rows),
                    "reviewable_claim_rows": int(rows["reviewable_legal_claim"].fillna(False).astype(bool).sum()),
                    "citation_gate_issue_rows": int(rows["entailment_label"].isin(issue_labels).sum()),
                    "release_blocker_rows": int(rows["entailment_label"].isin(release_blockers).sum()),
                    "supported_rows": int((rows["entailment_label"] == "supported").sum()),
                    "partially_supported_rows": int((rows["entailment_label"] == "partially_supported").sum()),
                    "unsupported_rows": int((rows["entailment_label"] == "unsupported").sum()),
                    "no_citation_rows": int((rows["entailment_label"] == "no_citation").sum()),
                    "out_of_scope_source_rows": int((rows["entailment_label"] == "out_of_scope_source").sum()),
                    "fabricated_citation_rows": int((rows["entailment_label"] == "fabricated_citation").sum()),
                    "contradicted_rows": int((rows["entailment_label"] == "contradicted").sum()),
                }
            ]
        )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    return result


def verify_output_citations(
    *,
    run_row: dict[str, Any],
    contexts: list[dict[str, Any]],
    output_text: str,
) -> dict[str, Any]:
    retrieved_ids = {safe_text(item.get("source_id")) for item in contexts}
    cited_ids = set(_parse_source_ids(output_text))
    fabricated = sorted(cited_ids - retrieved_ids)
    valid = sorted(cited_ids.intersection(retrieved_ids))
    claim_checks = verify_claims(output_text, contexts)
    unsupported_claims = [
        check
        for check in claim_checks
        if check["support_label"] in {"weak_or_unsupported_cited_claim", "uncited_or_unsupported_claim"}
    ]
    requires_citation = safe_text(run_row.get("version")) in {"V3", "V4"} and bool(contexts)
    if fabricated:
        label = "fabricated_citation"
    elif unsupported_claims:
        label = "unsupported_claim"
    elif requires_citation and not cited_ids:
        label = "missing_citation"
    elif valid:
        label = "citation_supported"
    else:
        label = "no_citation_required"
    return {
        "run_id": run_row["run_id"],
        "sample_id": safe_text(run_row["sample_id"]),
        "model_alias": safe_text(run_row.get("model_alias")),
        "version": safe_text(run_row.get("version")),
        "workflow_condition": safe_text(run_row.get("workflow_condition")),
        "retrieved_source_ids": json_dumps(sorted(retrieved_ids)),
        "cited_source_ids": json_dumps(sorted(cited_ids)),
        "valid_citation_ids": json_dumps(valid),
        "fabricated_citation_ids": json_dumps(fabricated),
        "citation_count": len(cited_ids),
        "valid_citation_count": len(valid),
        "fabricated_citation_count": len(fabricated),
        "claim_count": len(claim_checks),
        "unsupported_claim_count": len(unsupported_claims),
        "claim_checks": json_dumps(claim_checks),
        "citation_fidelity_label": label,
    }
