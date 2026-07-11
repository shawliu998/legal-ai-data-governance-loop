from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .product_boundary_dataset import load_product_boundary_cases
from .release_gate import (
    CLAIM_ENTAILMENT_BLOCKER_LABELS,
    CLAIM_ENTAILMENT_ISSUE_LABELS,
    CLAIM_ENTAILMENT_STRICT_DEFECT_LABELS,
)
from .utils import json_loads_or_none, parse_bool, safe_text


DEFAULT_RAG_V2_FOCUS_CASES = [
    "LPB-CITE-001",
    "LPB-CITE-002",
    "LPB-CITE-003",
    "LPB-CITE-004",
    "LPB-CITE-005",
    "LPB-CITE-006",
    "LPB-CITE-007",
    "LPB-CITE-008",
]


def _json_list(value: Any) -> list[str]:
    parsed = json_loads_or_none(value)
    if isinstance(parsed, list):
        return [safe_text(item) for item in parsed if safe_text(item)]
    if safe_text(value):
        return [safe_text(value)]
    return []


def _as_bool(value: Any) -> bool:
    return parse_bool(value)


def _rate(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _sha12(text: Any) -> str:
    return hashlib.sha256(safe_text(text).encode("utf-8")).hexdigest()[:12]


def _file_sha256(path: str | Path | None) -> str:
    if not path:
        return ""
    source = Path(path)
    if not source.exists():
        return ""
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_value(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=Path(__file__).resolve().parents[2],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def _working_tree_state() -> str:
    value = _git_value(
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--",
        ".",
        ":(exclude)outputs/**",
    )
    if value == "unknown":
        return "unknown"
    return "dirty" if value else "clean"


def _case_rows(cases_jsonl: str | Path, focus_cases: list[str]) -> pd.DataFrame:
    case_by_id = {safe_text(case.get("case_id")): case for case in load_product_boundary_cases(cases_jsonl)}
    rows = []
    for sample_id in focus_cases:
        case = case_by_id.get(sample_id, {})
        rows.append(
            {
                "sample_id": sample_id,
                "slice": safe_text(case.get("slice")),
                "task_type": safe_text(case.get("task_type")),
                "allowed_source_ids": _json_list(case.get("allowed_sources", [])),
                "allowed_source_count": len(_json_list(case.get("allowed_sources", []))),
                "expected_human_review": bool(case.get("expected_human_review", False)),
            }
        )
    return pd.DataFrame(rows)


def _retrieval_metrics(retrieval: pd.DataFrame, cases: pd.DataFrame) -> pd.DataFrame:
    if retrieval.empty:
        return pd.DataFrame(columns=["run_id"])
    allowed_by_sample = {row["sample_id"]: set(row["allowed_source_ids"]) for _, row in cases.iterrows()}
    rows = []
    for _, row in retrieval.iterrows():
        sample_id = safe_text(row.get("sample_id"))
        retrieved = _json_list(row.get("retrieved_source_ids"))
        expected = _json_list(row.get("expected_source_ids"))
        allowed = allowed_by_sample.get(sample_id, set())
        retrieved_set = set(retrieved)
        expected_set = set(expected)
        allowed_hits = retrieved_set.intersection(allowed)
        expected_hits = retrieved_set.intersection(expected_set)
        rows.append(
            {
                "run_id": safe_text(row.get("run_id")),
                "sample_id": sample_id,
                "model_alias": safe_text(row.get("model_alias")),
                "version": safe_text(row.get("version")),
                "workflow_condition": safe_text(row.get("workflow_condition")),
                "retrieved_count": len(retrieved_set),
                "allowed_source_count": len(allowed),
                "allowed_retrieved_count": len(allowed_hits),
                "source_boundary_precision": _rate(len(allowed_hits), len(retrieved_set)) if allowed else "",
                "allowed_source_recall": _rate(len(allowed_hits), len(allowed)) if allowed else "",
                "expected_source_count": len(expected_set),
                "expected_source_hit_count": len(expected_hits),
                "context_recall": _rate(len(expected_hits), len(expected_set)) if expected_set else "",
                "context_precision": _rate(len(expected_hits), len(retrieved_set)) if expected_set else "",
                "retrieval_status": safe_text(row.get("retrieval_status")),
            }
        )
    return pd.DataFrame(rows)


def _claim_metrics(claims: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "run_id",
        "claim_rows",
        "reviewable_claim_count",
        "cited_reviewable_claim_count",
        "citation_coverage_rate",
        "reviewable_strict_citation_defect_count",
        "reviewable_claim_needs_review_count",
        "reviewable_citation_issue_count",
        "citation_gate_issue_count",
        "citation_gate_issue_rate",
        "all_claim_source_boundary_blocker_count",
        "all_claim_source_boundary_blocker_rate",
        "claim_release_blocker_count",
        "claim_supported_count",
        "claim_partially_supported_count",
        "claim_unsupported_count",
        "claim_no_citation_count",
        "claim_out_of_scope_source_count",
        "claim_fabricated_citation_count",
        "claim_contradicted_count",
    ]
    if claims.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    claims = claims.copy()
    claims["reviewable_legal_claim"] = claims["reviewable_legal_claim"].map(_as_bool)
    claims["has_citation"] = claims["cited_source_ids"].map(lambda value: bool(_json_list(value)))
    for run_id, group in claims.groupby("run_id", sort=False):
        labels = group["entailment_label"].fillna("")
        reviewable = group[group["reviewable_legal_claim"]]
        reviewable_labels = reviewable["entailment_label"].fillna("")
        strict_defect_count = int(
            reviewable_labels.isin(CLAIM_ENTAILMENT_STRICT_DEFECT_LABELS).sum()
        )
        reviewable_issue_count = int(reviewable_labels.isin(CLAIM_ENTAILMENT_ISSUE_LABELS).sum())
        all_claim_blockers = int(labels.isin(CLAIM_ENTAILMENT_BLOCKER_LABELS).sum())
        rows.append(
            {
                "run_id": safe_text(run_id),
                "claim_rows": int(len(group)),
                "reviewable_claim_count": int(len(reviewable)),
                "cited_reviewable_claim_count": int(reviewable["has_citation"].sum()),
                "citation_coverage_rate": _rate(int(reviewable["has_citation"].sum()), len(reviewable)),
                "reviewable_strict_citation_defect_count": strict_defect_count,
                "reviewable_claim_needs_review_count": reviewable_issue_count,
                "reviewable_citation_issue_count": reviewable_issue_count,
                # Backward-compatible name; numerator is reviewable-only.
                "citation_gate_issue_count": reviewable_issue_count,
                "citation_gate_issue_rate": _rate(reviewable_issue_count, len(reviewable)),
                "all_claim_source_boundary_blocker_count": all_claim_blockers,
                "all_claim_source_boundary_blocker_rate": _rate(all_claim_blockers, len(group)),
                # Deprecated compatibility alias.  This remains an all-claim
                # count and must never be divided by reviewable_claim_count.
                "claim_release_blocker_count": all_claim_blockers,
                "claim_supported_count": int((labels == "supported").sum()),
                "claim_partially_supported_count": int((labels == "partially_supported").sum()),
                "claim_unsupported_count": int((labels == "unsupported").sum()),
                "claim_no_citation_count": int((labels == "no_citation").sum()),
                "claim_out_of_scope_source_count": int((labels == "out_of_scope_source").sum()),
                "claim_fabricated_citation_count": int((labels == "fabricated_citation").sum()),
                "claim_contradicted_count": int((labels == "contradicted").sum()),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _read_optional_csv(path: str | Path | None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path).fillna("")


def _write_readme(output_dir: Path, metrics: dict[str, Any], focus_cases: list[str]) -> None:
    lines = [
        "# RAG V2 Focused Pilot Evidence Package",
        "",
        "This directory contains a lightweight evidence package for the RAG V2 focused pilot.",
        "",
        "The pilot focuses on source-limited legal QA and document-interpretation cases. It separates retrieval quality from answer quality, then turns citation and claim failures into product release-gate and data-production signals.",
        "",
        "## Scope",
        "",
        f"- Focus cases: {len(focus_cases)}",
        f"- Model-workflow API run records analyzed: {metrics.get('api_run_records', 0)}",
        f"- RAG retrieval rows: {metrics.get('retrieval_rows', 0)}",
        f"- Claim rows analyzed: {metrics.get('claim_rows', 0)}",
        f"- Strict citation-defect flag rate: {metrics.get('reviewable_claim_strict_citation_defect_rate', 0)}",
        f"- Claim-support needs-review rate: {metrics.get('reviewable_claim_needs_review_rate', 0)}",
        f"- All-claim source-boundary blocker count: {metrics.get('all_claim_source_boundary_blocker_rows', 0)}",
        f"- All-claim source-boundary blocker rate: {metrics.get('all_claim_source_boundary_blocker_rate', 0)}",
        "",
        "## Included",
        "",
        "- `metrics_summary.csv`: high-level RAG V2 metrics.",
        "- `workflow_comparison.csv`: workflow-level quality and risk comparison.",
        "- `model_workflow_summary.csv`: model-workflow deployment signals.",
        "- `failure_taxonomy.csv`: failure labels and data-routing actions.",
        "- `source_boundary_summary.csv`: retrieval source-boundary and expected-source checks.",
        "- `redacted_sample_outputs_20.csv`: representative rows with output length and hash only.",
        "- `artifact_manifest.yaml`: machine-readable manifest and caveats.",
        "",
        "## Caveats",
        "",
        "- This is a focused citation-grounding pilot, not a full legal knowledge-base benchmark.",
        "- Claim entailment labels are deterministic triage signals, not final legal conclusions.",
        "- Qwen judge scores, if present, are baseline signals and should not be treated as final model rankings.",
        "- Full raw model outputs remain local/ignored; this package commits summaries and redacted samples only.",
    ]
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_rag_v2_report(
    *,
    runs_path: str | Path,
    retrieval_path: str | Path,
    citation_path: str | Path,
    claim_entailment_path: str | Path,
    cases_jsonl: str | Path,
    output_dir: str | Path,
    judge_scores_path: str | Path | None = None,
    routing_path: str | Path | None = None,
    release_gate_path: str | Path | None = None,
    focus_cases: list[str] | None = None,
    focus_versions: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    focus_cases = focus_cases or DEFAULT_RAG_V2_FOCUS_CASES
    focus_versions = focus_versions or ["V1", "V4", "V5"]

    runs = pd.read_csv(runs_path).fillna("")
    retrieval = _read_optional_csv(retrieval_path)
    citations = _read_optional_csv(citation_path)
    claims = _read_optional_csv(claim_entailment_path)
    scores = _read_optional_csv(judge_scores_path)
    routing = _read_optional_csv(routing_path)
    release_gate = _read_optional_csv(release_gate_path)
    cases = _case_rows(cases_jsonl, focus_cases)

    runs = runs[runs["sample_id"].isin(focus_cases) & runs["version"].isin(focus_versions)].copy()
    run_ids = set(runs["run_id"])
    retrieval = retrieval[retrieval["run_id"].isin(run_ids)].copy() if not retrieval.empty else retrieval
    citations = citations[citations["run_id"].isin(run_ids)].copy() if not citations.empty else citations
    claims = claims[claims["run_id"].isin(run_ids)].copy() if not claims.empty else claims
    scores = scores[scores["run_id"].isin(run_ids)].copy() if not scores.empty else scores
    routing = routing[routing["run_id"].isin(run_ids)].copy() if not routing.empty else routing

    retrieval_by_run = _retrieval_metrics(retrieval, cases)
    claim_by_run = _claim_metrics(claims)
    runs["output_character_count"] = runs["output_text"].map(lambda text: len(safe_text(text)))
    runs["output_sha256_12"] = runs["output_text"].map(_sha12)

    merged = runs.merge(cases, on="sample_id", how="left")
    for frame in [scores, routing, citations, retrieval_by_run, claim_by_run]:
        if not frame.empty:
            merge_cols = [col for col in frame.columns if col not in merged.columns or col == "run_id"]
            merged = merged.merge(frame[merge_cols], on="run_id", how="left")
    numeric_cols = [
        "score_rate",
        "citation_count",
        "valid_citation_count",
        "fabricated_citation_count",
        "unsupported_claim_count",
        "claim_rows",
        "reviewable_claim_count",
        "cited_reviewable_claim_count",
        "reviewable_strict_citation_defect_count",
        "reviewable_claim_needs_review_count",
        "reviewable_citation_issue_count",
        "citation_gate_issue_count",
        "all_claim_source_boundary_blocker_count",
        "all_claim_source_boundary_blocker_rate",
        "claim_release_blocker_count",
        "claim_no_citation_count",
        "claim_out_of_scope_source_count",
        "claim_fabricated_citation_count",
        "claim_contradicted_count",
        "latency_ms",
        "estimated_cost",
    ]
    for col in numeric_cols:
        if col not in merged.columns:
            merged[col] = 0
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)
    if "needs_human_review" in merged.columns:
        merged["needs_human_review"] = merged["needs_human_review"].map(_as_bool)
    else:
        merged["needs_human_review"] = False

    api_run_records = len(merged)
    claim_rows = len(claims)
    reviewable_claims = int(claims["reviewable_legal_claim"].map(_as_bool).sum()) if not claims.empty else 0
    if not claims.empty:
        reviewable_claim_rows = claims[claims["reviewable_legal_claim"].map(_as_bool)]
        strict_defect_claims = int(
            reviewable_claim_rows["entailment_label"].isin(
                CLAIM_ENTAILMENT_STRICT_DEFECT_LABELS
            ).sum()
        )
        issue_claims = int(reviewable_claim_rows["entailment_label"].isin(CLAIM_ENTAILMENT_ISSUE_LABELS).sum())
    else:
        strict_defect_claims = 0
        issue_claims = 0
    blocker_claims = int(claims["entailment_label"].isin(CLAIM_ENTAILMENT_BLOCKER_LABELS).sum()) if not claims.empty else 0
    metrics = {
        "focus_cases": len(focus_cases),
        "api_run_records": api_run_records,
        "models": merged["model_alias"].nunique() if api_run_records else 0,
        "workflow_versions": merged["version"].nunique() if api_run_records else 0,
        "retrieval_rows": len(retrieval),
        "claim_rows": claim_rows,
        "reviewable_claim_rows": reviewable_claims,
        "reviewable_claim_strict_citation_defect_rows": strict_defect_claims,
        "reviewable_claim_strict_citation_defect_rate": _rate(strict_defect_claims, reviewable_claims),
        "reviewable_claim_needs_review_rows": issue_claims,
        "reviewable_claim_needs_review_rate": _rate(issue_claims, reviewable_claims),
        "all_claim_source_boundary_blocker_rows": blocker_claims,
        "all_claim_source_boundary_blocker_rate": _rate(blocker_claims, claim_rows),
        "judge_rows": len(scores),
        "avg_score_rate": round(float(merged["score_rate"].mean()), 4) if "score_rate" in merged else 0.0,
        "human_review_rate": round(float(merged["needs_human_review"].mean()), 4) if api_run_records else 0.0,
        "raw_outputs_committed": False,
    }
    metrics_df = pd.DataFrame([{"metric": key, "value": value} for key, value in metrics.items()])
    metrics_df.to_csv(output / "metrics_summary.csv", index=False, encoding="utf-8-sig")

    workflow_rows = []
    for version, group in merged.groupby("version", sort=True):
        workflow_rows.append(
            {
                "version": version,
                "workflow_condition": safe_text(group["workflow_condition"].iloc[0]),
                "workflow_name": safe_text(group["workflow_name"].iloc[0]),
                "runs": int(len(group)),
                "avg_score_rate": round(float(group["score_rate"].mean()), 4),
                "human_review_rate": round(float(group["needs_human_review"].mean()), 4),
                "avg_latency_ms": round(float(group["latency_ms"].mean()), 2),
                "citation_coverage_rate": _rate(group["cited_reviewable_claim_count"].sum(), group["reviewable_claim_count"].sum()),
                "reviewable_strict_citation_defect_count": int(
                    group["reviewable_strict_citation_defect_count"].sum()
                ),
                "reviewable_strict_citation_defect_rate": _rate(
                    group["reviewable_strict_citation_defect_count"].sum(),
                    group["reviewable_claim_count"].sum(),
                ),
                "reviewable_claim_needs_review_count": int(
                    group["reviewable_claim_needs_review_count"].sum()
                ),
                "reviewable_claim_needs_review_rate": _rate(
                    group["reviewable_claim_needs_review_count"].sum(),
                    group["reviewable_claim_count"].sum(),
                ),
                "all_claim_source_boundary_blocker_count": int(
                    group["all_claim_source_boundary_blocker_count"].sum()
                ),
                "all_claim_source_boundary_blocker_rate": _rate(
                    group["all_claim_source_boundary_blocker_count"].sum(), group["claim_rows"].sum()
                ),
                "no_citation_claims": int(group["claim_no_citation_count"].sum()),
                "out_of_scope_source_claims": int(group["claim_out_of_scope_source_count"].sum()),
                "fabricated_claim_citations": int(group["claim_fabricated_citation_count"].sum()),
                "contradicted_claims": int(group["claim_contradicted_count"].sum()),
            }
        )
    workflow_comparison = pd.DataFrame(workflow_rows)
    workflow_comparison.to_csv(output / "workflow_comparison.csv", index=False, encoding="utf-8-sig")

    model_workflow_rows = []
    for keys, group in merged.groupby(["model_alias", "version"], sort=True):
        model_alias, version = keys
        model_workflow_rows.append(
            {
                "model_alias": model_alias,
                "version": version,
                "workflow_condition": safe_text(group["workflow_condition"].iloc[0]),
                "runs": int(len(group)),
                "avg_score_rate": round(float(group["score_rate"].mean()), 4),
                "human_review_rate": round(float(group["needs_human_review"].mean()), 4),
                "citation_coverage_rate": _rate(group["cited_reviewable_claim_count"].sum(), group["reviewable_claim_count"].sum()),
                "reviewable_strict_citation_defect_count": int(
                    group["reviewable_strict_citation_defect_count"].sum()
                ),
                "reviewable_strict_citation_defect_rate": _rate(
                    group["reviewable_strict_citation_defect_count"].sum(),
                    group["reviewable_claim_count"].sum(),
                ),
                "reviewable_claim_needs_review_count": int(
                    group["reviewable_claim_needs_review_count"].sum()
                ),
                "reviewable_claim_needs_review_rate": _rate(
                    group["reviewable_claim_needs_review_count"].sum(),
                    group["reviewable_claim_count"].sum(),
                ),
                "all_claim_source_boundary_blocker_count": int(
                    group["all_claim_source_boundary_blocker_count"].sum()
                ),
                "all_claim_source_boundary_blocker_rate": _rate(
                    group["all_claim_source_boundary_blocker_count"].sum(), group["claim_rows"].sum()
                ),
                "release_gate_decision": _release_gate_decision_from_group(group),
                "release_gate_reason": _release_gate_reason_from_group(group),
            }
        )
    model_workflow_summary = pd.DataFrame(model_workflow_rows)
    model_workflow_summary.to_csv(output / "model_workflow_summary.csv", index=False, encoding="utf-8-sig")

    if not claims.empty:
        failure_taxonomy = (
            claims.groupby(["entailment_label", "product_action"], dropna=False)
            .size()
            .reset_index(name="claim_count")
            .sort_values(["claim_count", "entailment_label"], ascending=[False, True])
        )
    else:
        failure_taxonomy = pd.DataFrame(columns=["entailment_label", "product_action", "claim_count"])
    failure_taxonomy.to_csv(output / "failure_taxonomy.csv", index=False, encoding="utf-8-sig")

    source_case_cols = ["sample_id", "slice", "task_type", "allowed_source_ids", "expected_human_review"]
    source_boundary_summary = (
        retrieval_by_run.merge(cases[source_case_cols], on="sample_id", how="left")
        if not retrieval_by_run.empty
        else retrieval_by_run
    )
    source_boundary_summary.to_csv(output / "source_boundary_summary.csv", index=False, encoding="utf-8-sig")

    sample_sort_cols = [
        "all_claim_source_boundary_blocker_count",
        "reviewable_claim_needs_review_count",
        "needs_human_review",
        "score_rate",
    ]
    samples = merged.sort_values(sample_sort_cols, ascending=[False, False, False, True]).head(20).copy()
    redacted_cols = [
        "run_id",
        "sample_id",
        "model_alias",
        "version",
        "workflow_condition",
        "score_rate",
        "needs_human_review",
        "citation_fidelity_label",
        "claim_rows",
        "reviewable_claim_count",
        "reviewable_strict_citation_defect_count",
        "reviewable_claim_needs_review_count",
        "all_claim_source_boundary_blocker_count",
        "all_claim_source_boundary_blocker_rate",
        "claim_no_citation_count",
        "claim_out_of_scope_source_count",
        "claim_fabricated_citation_count",
        "claim_contradicted_count",
        "output_character_count",
        "output_sha256_12",
    ]
    for col in redacted_cols:
        if col not in samples.columns:
            samples[col] = ""
    samples[redacted_cols].assign(
        redaction_note="full output text and free-form judge reason omitted; raw output remains local/ignored"
    ).to_csv(output / "redacted_sample_outputs_20.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "schema_version": "2.0",
        "package": "rag_v2_focused_pilot_lightweight_evidence",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "base_git_commit": _git_value("rev-parse", "HEAD"),
        "working_tree_state": _working_tree_state(),
        "working_tree_scope": "source_and_configuration_excluding_outputs",
        "purpose": "Focused RAG V2 evidence package for citation grounding, source-boundary precision, and claim-level release gates.",
        "source_run": {
            "focus_cases": focus_cases,
            "workflow_versions": focus_versions,
            "api_run_records": api_run_records,
            "retrieval_rows": len(retrieval),
            "claim_rows": claim_rows,
            "model_aliases": sorted(merged["model_alias"].dropna().astype(str).unique().tolist()),
        },
        "source_artifact_sha256": {
            "runs": _file_sha256(runs_path),
            "retrieval": _file_sha256(retrieval_path),
            "citation_verification": _file_sha256(citation_path),
            "claim_entailment": _file_sha256(claim_entailment_path),
            "cases_jsonl": _file_sha256(cases_jsonl),
            "judge_scores": _file_sha256(judge_scores_path),
            "routing": _file_sha256(routing_path),
            "release_gate": _file_sha256(release_gate_path),
        },
        "reproducibility_inputs_sha256": {
            "pilot_config": _file_sha256(
                Path(__file__).resolve().parents[2]
                / "configs/pilots/qianfan_rag_v2_focused.yaml"
            ),
            "evaluation_implementation": _file_sha256(Path(__file__)),
        },
        "methodology_caveats": [
            "Focused citation/document slice, not a full legal knowledge-base benchmark.",
            "Claim entailment labels are deterministic triage signals, not final legal conclusions.",
            "Strict citation-defect flags exclude partially supported claims and use reviewable legal claims only.",
            "Needs-review counts include partially supported claims and are used by the release gate.",
            "Source-boundary blocker counts scan all claim rows; blocker rates use all claim rows as denominator.",
            "Qwen judge scores are baseline signals and should not be treated as final model rankings.",
            "Raw full model outputs remain local/ignored; this package commits summaries and redacted samples only.",
        ],
        "metric_definitions": {
            "reviewable_claim_strict_citation_defect_rows": "reviewable claims labeled unsupported, contradicted, no_citation, out_of_scope_source, or fabricated_citation",
            "reviewable_claim_needs_review_rows": "strict citation defects plus partially_supported reviewable claims",
            "all_claim_source_boundary_blocker_rows": "all claim rows labeled out_of_scope_source, fabricated_citation, or contradicted",
        },
        "included_artifacts": [
            "README.md",
            "artifact_manifest.yaml",
            "metrics_summary.csv",
            "workflow_comparison.csv",
            "model_workflow_summary.csv",
            "failure_taxonomy.csv",
            "source_boundary_summary.csv",
            "redacted_sample_outputs_20.csv",
        ],
        "excluded_artifacts": [
            "Full model_run_log.csv, judge_scores.csv, claim_entailment.csv, citation_verification.csv, and raw output text."
        ],
    }
    (output / "artifact_manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    _write_readme(output, metrics, focus_cases)

    return {
        "metrics_summary": metrics_df,
        "workflow_comparison": workflow_comparison,
        "model_workflow_summary": model_workflow_summary,
        "failure_taxonomy": failure_taxonomy,
        "source_boundary_summary": source_boundary_summary,
    }


def _release_gate_decision_from_group(group: pd.DataFrame) -> str:
    reviewable = float(group["reviewable_claim_count"].sum())
    issue_rate = _rate(float(group["citation_gate_issue_count"].sum()), reviewable)
    blocker_count = int(group["claim_release_blocker_count"].sum())
    human_review_rate = float(group["needs_human_review"].mean()) if len(group) else 1.0
    avg_score = float(group["score_rate"].mean()) if len(group) else 0.0
    if blocker_count:
        return "blocked"
    if issue_rate > 0.25:
        return "limited_release"
    if human_review_rate > 0.5:
        return "limited_release"
    if avg_score >= 0.8 and issue_rate <= 0.1:
        return "candidate_auto_answer"
    return "limited_release"


def _release_gate_reason_from_group(group: pd.DataFrame) -> str:
    reviewable = float(group["reviewable_claim_count"].sum())
    issue_rate = _rate(float(group["citation_gate_issue_count"].sum()), reviewable)
    blocker_count = int(group["claim_release_blocker_count"].sum())
    human_review_rate = float(group["needs_human_review"].mean()) if len(group) else 1.0
    avg_score = float(group["score_rate"].mean()) if len(group) else 0.0
    if blocker_count:
        return "source_boundary_or_claim_support_blocker"
    if issue_rate > 0.25:
        return "claim_support_needs_review_rate_above_threshold"
    if human_review_rate > 0.5:
        return "majority_of_runs_require_human_review"
    if avg_score >= 0.8 and issue_rate <= 0.1:
        return "score_and_claim_support_thresholds_met"
    return "insufficient_evidence_for_auto_answer"
