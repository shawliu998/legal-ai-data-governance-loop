from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .dataset_builder import AGENT_VISIBLE_COLUMNS, BOUNDARY, GOLD_COLUMNS, JURISDICTION, LAW_SNAPSHOT_DATE, METADATA_COLUMNS
from .utils import safe_text


SOURCE_URLS = {
    "case": "https://raw.githubusercontent.com/SKYLENAGE-AI/PLawbench/main/practical_case_analysis_250.jsonl",
    "consultation": "https://raw.githubusercontent.com/SKYLENAGE-AI/PLawbench/main/public_legal_consultation_18.json",
    "defendant_statement": "https://raw.githubusercontent.com/SKYLENAGE-AI/PLawbench/main/Defendants_Statement.json",
    "plaintiff_statement": "https://raw.githubusercontent.com/SKYLENAGE-AI/PLawbench/main/Plantiffs_Statement.json",
}

SOURCE_FILENAMES = {
    "case": "practical_case_analysis_250.jsonl",
    "consultation": "public_legal_consultation_18.json",
    "defendant_statement": "Defendants_Statement.json",
    "plaintiff_statement": "Plantiffs_Statement.json",
}

SOURCE_DATASET = "external_practice_benchmark_adapted"


def _download_sources(source_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    for key, url in SOURCE_URLS.items():
        target = source_dir / SOURCE_FILENAMES[key]
        if target.exists():
            continue
        with urllib.request.urlopen(url, timeout=30) as response:
            target.write_bytes(response.read())


def _load_json(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _parse_points(text: str, default: int = 2) -> int:
    matches = re.findall(r"[+＋]\s*(\d+)\s*分|（\s*(\d+)\s*分\s*）|\((\d+)\s*分\)", text)
    points = [int(value) for match in matches for value in match if value]
    return max(points) if points else default


def _shorten(text: str, limit: int = 700) -> str:
    normalized = re.sub(r"\s+", " ", safe_text(text)).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"


def _split_numbered_rubric(text: str, *, fallback_dimension: str, max_items: int = 12) -> list[tuple[str, int, str]]:
    normalized = safe_text(text).replace("\r\n", "\n")
    candidates = re.split(r"\n(?=\s*\d+(?:[.、]|．))", normalized)
    items: list[tuple[str, int, str]] = []
    for candidate in candidates:
        cleaned = candidate.strip()
        if not cleaned or cleaned.startswith("总分"):
            continue
        if "分" not in cleaned and len(cleaned) < 12:
            continue
        items.append((fallback_dimension, _parse_points(cleaned), _shorten(cleaned, 900)))
        if len(items) >= max_items:
            break
    if items:
        return items
    return [(fallback_dimension, _parse_points(normalized), _shorten(normalized, 900))]


def _split_document_rubric(text: str, *, max_items: int = 12) -> list[tuple[str, int, str]]:
    normalized = safe_text(text).replace("\r\n", "\n")
    section_pattern = re.compile(r"\n(?=[一二三四五六七八九十]+[、.．])")
    sections = [section.strip() for section in section_pattern.split("\n" + normalized) if section.strip()]
    items: list[tuple[str, int, str]] = []
    for idx, section in enumerate(sections, start=1):
        if section.startswith("总分"):
            continue
        first_line = section.splitlines()[0].strip()
        dimension = re.sub(r"（.*?分.*?）|\(.*?分.*?\)", "", first_line).strip(" 、.．") or "Document Rubric"
        items.append((dimension, _parse_points(section, default=10), _shorten(section, 1000)))
        if len(items) >= max_items:
            break
    if items:
        return items
    return _split_numbered_rubric(normalized, fallback_dimension="Document Rubric", max_items=max_items)


def _case_dimension(tag: str) -> str:
    if "结论" in tag:
        return "Case Conclusion"
    if "案情" in tag or "事实" in tag:
        return "Legal Facts"
    if "分析" in tag or "推理" in tag:
        return "Legal Reasoning"
    if "法条" in tag or "依据" in tag:
        return "Statute Basis"
    return "Case Analysis"


def _rubric_row(
    *,
    sample_id: str,
    task_category: str,
    index: int,
    dimension: str,
    item: str,
    max_score: int,
    criticality: str = "medium",
) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "source_dataset": SOURCE_DATASET,
        "task_category": task_category,
        "rubric_id": f"{sample_id}-R{index:02d}",
        "rubric_dimension": dimension,
        "atomic_rubric_item": item,
        "max_score": int(max_score),
        "scoring_rule_2": "完整满足：覆盖该评分点的核心要素，并与案情事实或文书目的相连接。",
        "scoring_rule_1": "部分满足：提到相关方向，但缺少关键事实、限定条件、证据或法律适用说明。",
        "scoring_rule_0": "未满足/错误：未覆盖该点，或给出相反、武断、不可复核的表述。",
        "criticality": criticality,
        "negative_rule": "不得编造事实、伪造具体法条或在事实不足时给出确定性法律结论。",
    }


def _append_case_records(
    *,
    rows: list[dict[str, Any]],
    eval_records: list[dict[str, Any]],
    gold_records: list[dict[str, Any]],
    rubric_records: list[dict[str, Any]],
    metadata_records: list[dict[str, Any]],
    limit: int,
) -> None:
    for idx, item in enumerate(rows[:limit], start=1):
        sample_id = f"PB-CASE-{idx:03d}"
        context = safe_text(item.get("context"))
        question = safe_text(item.get("question"))
        label = safe_text(item.get("label")) or "实务案例"
        eval_records.append(
            {
                "sample_id": sample_id,
                "source_dataset": SOURCE_DATASET,
                "task_category": "case_analysis",
                "user_question": question,
                "known_facts": context,
                "legal_concepts": label,
                "jurisdiction": JURISDICTION,
                "law_snapshot_date": LAW_SNAPSHOT_DATE,
                "task_type": "practical_case_analysis",
                "legal_advice_boundary": BOUNDARY,
            }
        )
        rubrics = item.get("rubrics") or []
        expected = "；".join(_shorten(safe_text(rubric.get("criterion")), 180) for rubric in rubrics)
        gold_records.append(
            {
                "sample_id": sample_id,
                "source_dataset": SOURCE_DATASET,
                "task_category": "case_analysis",
                "key_missing_facts": "依据案情材料识别关键法律事实；不得补充案情外事实。",
                "expected_clarification_questions": "本任务为单轮案例分析；如事实不足，应明确列出需补充的证据或事实。",
                "expected_answer_points": expected,
                "risk_points": "主要风险包括结论跳跃、事实归纳遗漏、法律依据错误或编造、推理链与案情脱节。",
                "expected_behavior": "按结论、事实、推理、依据组织分析，并保持条件化结论。",
                "human_review_note": "practice benchmark adapted case-analysis sample.",
            }
        )
        for r_idx, rubric in enumerate(rubrics, start=1):
            criterion = safe_text(rubric.get("criterion"))
            rubric_records.append(
                _rubric_row(
                    sample_id=sample_id,
                    task_category="case_analysis",
                    index=r_idx,
                    dimension=_case_dimension(safe_text(rubric.get("tags"))),
                    item=_shorten(criterion, 1000),
                    max_score=int(float(safe_text(rubric.get("points")) or _parse_points(criterion, 5))),
                    criticality="high" if r_idx <= 2 else "medium",
                )
            )
        metadata_records.append(_metadata_row(sample_id, "case_analysis", label, "medium", "medium"))


def _append_consultation_records(
    *,
    rows: list[dict[str, Any]],
    eval_records: list[dict[str, Any]],
    gold_records: list[dict[str, Any]],
    rubric_records: list[dict[str, Any]],
    metadata_records: list[dict[str, Any]],
    limit: int,
) -> None:
    for idx, item in enumerate(rows[:limit], start=1):
        sample_id = f"PB-CONS-{idx:03d}"
        conversation = safe_text(item.get("conversation"))
        rubric_text = safe_text(item.get("rubrics"))
        eval_records.append(
            {
                "sample_id": sample_id,
                "source_dataset": SOURCE_DATASET,
                "task_category": "consultation",
                "user_question": "请作为律师根据当事人陈述提出关键追问，并避免在事实不足时直接给出确定性结论。",
                "known_facts": conversation,
                "legal_concepts": "公众法律咨询、事实追问、风险识别",
                "jurisdiction": JURISDICTION,
                "law_snapshot_date": LAW_SNAPSHOT_DATE,
                "task_type": "public_legal_consultation",
                "legal_advice_boundary": BOUNDARY,
            }
        )
        gold_records.append(
            {
                "sample_id": sample_id,
                "source_dataset": SOURCE_DATASET,
                "task_category": "consultation",
                "key_missing_facts": rubric_text,
                "expected_clarification_questions": rubric_text,
                "expected_answer_points": "输出应以关键追问为主，覆盖身份关系、证据材料、时间节点、程序状态和高风险行动边界。",
                "risk_points": "主要风险包括被情绪化叙述带偏、遗漏关键事实、提前承诺结果、给出高风险行动建议。",
                "expected_behavior": "先追问关键事实，再给出谨慎的信息性分析边界。",
                "human_review_note": "practice benchmark adapted consultation sample.",
            }
        )
        for r_idx, (dimension, points, rubric_item) in enumerate(
            _split_numbered_rubric(rubric_text, fallback_dimension="Clarification Coverage"),
            start=1,
        ):
            rubric_records.append(
                _rubric_row(
                    sample_id=sample_id,
                    task_category="consultation",
                    index=r_idx,
                    dimension=dimension,
                    item=rubric_item,
                    max_score=points,
                    criticality="high" if r_idx <= 3 else "medium",
                )
            )
        metadata_records.append(_metadata_row(sample_id, "consultation", "公众法律咨询", "hard", "high"))


def _append_document_records(
    *,
    rows: list[dict[str, Any]],
    prefix: str,
    doc_type: str,
    eval_records: list[dict[str, Any]],
    gold_records: list[dict[str, Any]],
    rubric_records: list[dict[str, Any]],
    metadata_records: list[dict[str, Any]],
    limit: int,
) -> None:
    for idx, item in enumerate(rows[:limit], start=1):
        sample_id = f"PB-DOC-{prefix}-{idx:03d}"
        conversation = safe_text(item.get("conversation"))
        rubric_text = safe_text(item.get("Rubrics") or item.get("rubrics"))
        tag = safe_text(item.get("tag")) or doc_type
        eval_records.append(
            {
                "sample_id": sample_id,
                "source_dataset": SOURCE_DATASET,
                "task_category": "document_drafting",
                "user_question": conversation,
                "known_facts": "当事人陈述包含文书起草目标、争议事实和部分诉求；需整理为可审查的法律文书框架。",
                "legal_concepts": tag,
                "jurisdiction": JURISDICTION,
                "law_snapshot_date": LAW_SNAPSHOT_DATE,
                "task_type": doc_type,
                "legal_advice_boundary": BOUNDARY,
            }
        )
        gold_records.append(
            {
                "sample_id": sample_id,
                "source_dataset": SOURCE_DATASET,
                "task_category": "document_drafting",
                "key_missing_facts": "需识别文书主体、案由/请求、事实证据、程序要求和高风险表述。",
                "expected_clarification_questions": "如缺少主体信息、法院/管辖、证据附件、金额计算或授权材料，应在文书前置说明中列明。",
                "expected_answer_points": rubric_text,
                "risk_points": "主要风险包括诉请不当、事实虚构、证据遗漏、程序路径错误、文书语气过度确定。",
                "expected_behavior": "按文书结构输出，区分可写入内容、待核实事实和证据附件。",
                "human_review_note": f"practice benchmark adapted {doc_type} sample.",
            }
        )
        for r_idx, (dimension, points, rubric_item) in enumerate(_split_document_rubric(rubric_text), start=1):
            rubric_records.append(
                _rubric_row(
                    sample_id=sample_id,
                    task_category="document_drafting",
                    index=r_idx,
                    dimension=dimension,
                    item=rubric_item,
                    max_score=points,
                    criticality="high" if r_idx <= 2 else "medium",
                )
            )
        metadata_records.append(_metadata_row(sample_id, "document_drafting", tag, "hard", "high"))


def _metadata_row(sample_id: str, task_category: str, legal_domain: str, difficulty: str, risk_level: str) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "source_dataset": SOURCE_DATASET,
        "task_category": task_category,
        "legal_domain": legal_domain,
        "difficulty": difficulty,
        "risk_level": risk_level,
        "visibility_policy": "Eval_Input visible to agent; gold/rubric visible only to judge and human review.",
        "core_sample_flag": "no",
        "deep_badcase_flag": "yes" if risk_level == "high" else "no",
        "human_review_required": "yes" if risk_level == "high" else "no",
    }


def prepare_practice_benchmark_dataset(
    *,
    output_dir: str | Path,
    source_dir: str | Path | None = None,
    download: bool = True,
    case_limit: int = 20,
    consultation_limit: int = 6,
    document_limit: int = 4,
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    source = Path(source_dir) if source_dir else output / "source"
    if download:
        _download_sources(source)

    case_rows = _load_jsonl(source / SOURCE_FILENAMES["case"])
    consultation_rows = _load_json(source / SOURCE_FILENAMES["consultation"])
    defendant_rows = _load_json(source / SOURCE_FILENAMES["defendant_statement"])
    plaintiff_rows = _load_json(source / SOURCE_FILENAMES["plaintiff_statement"])

    eval_records: list[dict[str, Any]] = []
    gold_records: list[dict[str, Any]] = []
    rubric_records: list[dict[str, Any]] = []
    metadata_records: list[dict[str, Any]] = []

    _append_case_records(
        rows=case_rows,
        eval_records=eval_records,
        gold_records=gold_records,
        rubric_records=rubric_records,
        metadata_records=metadata_records,
        limit=case_limit,
    )
    _append_consultation_records(
        rows=consultation_rows,
        eval_records=eval_records,
        gold_records=gold_records,
        rubric_records=rubric_records,
        metadata_records=metadata_records,
        limit=consultation_limit,
    )
    per_document_type = max(1, document_limit // 2)
    _append_document_records(
        rows=defendant_rows,
        prefix="D",
        doc_type="defense_statement_drafting",
        eval_records=eval_records,
        gold_records=gold_records,
        rubric_records=rubric_records,
        metadata_records=metadata_records,
        limit=per_document_type,
    )
    _append_document_records(
        rows=plaintiff_rows,
        prefix="P",
        doc_type="complaint_drafting",
        eval_records=eval_records,
        gold_records=gold_records,
        rubric_records=rubric_records,
        metadata_records=metadata_records,
        limit=document_limit - per_document_type,
    )

    pd.DataFrame(eval_records, columns=AGENT_VISIBLE_COLUMNS).to_csv(
        output / "eval_input.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(gold_records, columns=GOLD_COLUMNS).to_csv(
        output / "gold_labels.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(rubric_records).to_csv(output / "rubric_items.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(metadata_records, columns=METADATA_COLUMNS).to_csv(
        output / "sample_metadata.csv", index=False, encoding="utf-8-sig"
    )

    manifest = {
        "project": {
            "name": "Legal AI Practice Benchmark Pilot",
            "version": "0.1.0",
            "boundary": "pilot evaluation dataset; not legal advice; not model ranking",
        },
        "files": {
            "eval_input": "eval_input.csv",
            "gold_labels": "gold_labels.csv",
            "rubric_items": "rubric_items.csv",
            "sample_metadata": "sample_metadata.csv",
        },
        "sources": [
            {
                "source_dataset": SOURCE_DATASET,
                "expected_samples": len(eval_records),
                "role": "externally sourced adapted legal-practice pilot cases",
                "license_status": "not recorded in the local dataset manifest; verify upstream before redistribution",
                "upstream_urls": SOURCE_URLS,
            }
        ],
        "task_categories": ["consultation", "case_analysis", "document_drafting"],
        "visibility_policy": {
            "agent_visible": "Eval_Input only",
            "judge_visible": "Eval_Input + Gold_Labels + Rubric_Items",
        },
    }
    manifest_path = output / "dataset_manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return {
        "manifest": manifest_path,
        "eval_input": output / "eval_input.csv",
        "gold_labels": output / "gold_labels.csv",
        "rubric_items": output / "rubric_items.csv",
        "sample_metadata": output / "sample_metadata.csv",
    }
