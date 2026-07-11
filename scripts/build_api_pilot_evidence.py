#!/usr/bin/env python3
"""Build the lightweight, public evidence package from local pilot artifacts.

The raw model answers and reviewer workbooks stay local. This script computes
all public counts from those raw artifacts so README numbers are not hand-edited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PILOT_DIR = ROOT / "outputs/product_boundary_api_pilot_v1"
SOURCE_FILES = {
    "runs": "model_run_log.csv",
    "scores": "judge_scores.csv",
    "routing": "data_routing.csv",
    "release_gate": "release_gate.csv",
    "retrieval": "retrieval_log.csv",
    "citation": "citation_verification.csv",
    "claims": "claim_entailment.csv",
    "review": "human_review_priority_80_reviewed.csv",
}
STRICT_CITATION_DEFECT_LABELS = {
    "unsupported",
    "contradicted",
    "no_citation",
    "out_of_scope_source",
    "fabricated_citation",
}
CLAIM_NEEDS_REVIEW_LABELS = STRICT_CITATION_DEFECT_LABELS | {"partially_supported"}
SOURCE_BOUNDARY_BLOCKER_LABELS = {"out_of_scope_source", "fabricated_citation", "contradicted"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(str(file_path.relative_to(path)).encode("utf-8"))
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


def _git_value(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def _source_working_tree_state() -> str:
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


def _bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def _nonempty(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().ne("")


def _read_sources(source_dir: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    for key, filename in SOURCE_FILES.items():
        path = source_dir / filename
        if not path.exists():
            missing.append(filename)
            continue
        frames[key] = pd.read_csv(path).fillna("")
    if missing:
        raise SystemExit(f"Missing local source artifacts: {', '.join(missing)}")
    return frames


def _metric(metric: str, value: Any, note: str) -> dict[str, Any]:
    return {"metric": metric, "value": value, "note": note}


def _reviewer_pair_mask(review: pd.DataFrame) -> pd.Series:
    a_column = next(
        (name for name in ["reviewer_a_triage_label", "reviewer_a_label"] if name in review.columns),
        None,
    )
    b_column = next(
        (name for name in ["reviewer_b_triage_label", "reviewer_b_label"] if name in review.columns),
        None,
    )
    if not a_column or not b_column:
        return pd.Series(False, index=review.index)
    return _nonempty(review[a_column]) & _nonempty(review[b_column])


def _completed_final_review_mask(review: pd.DataFrame) -> pd.Series:
    required = [
        "human_pass_fail",
        "human_corrected_score_rate",
        "human_critical_failure",
        "human_citation_support",
        "human_route_override",
        "human_data_action",
    ]
    if any(column not in review.columns for column in required):
        return pd.Series(False, index=review.index)
    completed = pd.Series(True, index=review.index)
    for column in required:
        completed &= _nonempty(review[column])
    return completed


def build_metrics(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    runs = frames["runs"]
    scores = frames["scores"]
    routing = frames["routing"]
    gate = frames["release_gate"]
    retrieval = frames["retrieval"]
    citation = frames["citation"]
    claims = frames["claims"]
    review = frames["review"]

    has_answer = _nonempty(runs["output_text"])
    parsed_ok = _bool_series(scores["parsed_ok"]) if "parsed_ok" in scores else pd.Series(False, index=scores.index)
    reviewable = (
        _bool_series(claims["reviewable_legal_claim"])
        if "reviewable_legal_claim" in claims
        else claims["entailment_label"].ne("not_reviewable")
    )
    claim_label = claims["entailment_label"].astype(str)
    reviewable_strict_defect = reviewable & claim_label.isin(STRICT_CITATION_DEFECT_LABELS)
    reviewable_needs_review = reviewable & claim_label.isin(CLAIM_NEEDS_REVIEW_LABELS)
    source_boundary_blocker = claim_label.isin(SOURCE_BOUNDARY_BLOCKER_LABELS)

    rows = [
        _metric("api_run_count", len(runs), "Qianfan model x case x workflow API rows"),
        _metric("nonempty_answer_count", int(has_answer.sum()), "API runs with non-empty answer content"),
        _metric("empty_answer_count", int((~has_answer).sum()), "Completed API calls with empty answer content; reliability failures"),
        _metric("nonempty_answer_rate", round(float(has_answer.mean()), 4), "Availability metric, not legal-answer quality"),
        _metric("unique_cases", int(runs["sample_id"].nunique()), "Real pilot subset, not the full 50-case bank"),
        _metric("models", int(runs["model_alias"].nunique()), ", ".join(sorted(runs["model_alias"].unique()))),
        _metric("workflow_versions", int(runs["version"].nunique()), ", ".join(sorted(runs["version"].unique()))),
        _metric("judge_rows", len(scores), "Structured judge rows"),
        _metric("judge_parse_success", int(parsed_ok.sum()), "Parsing stability only; not judge accuracy"),
        _metric("judge_parse_success_rate", round(float(parsed_ok.mean()), 4), "Parsing stability only; not judge accuracy"),
        _metric("release_gate_group_count", len(gate), "task x model x workflow groups"),
        _metric("retrieval_log_rows", len(retrieval), "RAG-enabled retrieval rows"),
        _metric("citation_verification_rows", len(citation), "Deterministic citation-verification rows"),
        _metric("claim_row_count", len(claims), "All deterministic claim rows"),
        _metric("reviewable_claim_count", int(reviewable.sum()), "Rows eligible for legal-claim support review"),
        _metric(
            "reviewable_claim_strict_citation_defect_flag_count",
            int(reviewable_strict_defect.sum()),
            "Reviewable strict defects; excludes partially supported claims and is not a confirmed model-error count",
        ),
        _metric(
            "reviewable_claim_strict_citation_defect_flag_rate",
            round(float(reviewable_strict_defect.sum() / max(int(reviewable.sum()), 1)), 4),
            "Reviewable-only numerator and denominator; lower is better",
        ),
        _metric(
            "reviewable_claim_needs_review_count",
            int(reviewable_needs_review.sum()),
            "Strict defects plus partially supported reviewable claims; used by the release gate",
        ),
        _metric(
            "reviewable_claim_needs_review_rate",
            round(float(reviewable_needs_review.sum() / max(int(reviewable.sum()), 1)), 4),
            "Reviewable-only numerator and denominator; lower is better",
        ),
        _metric(
            "all_claim_source_boundary_blocker_count",
            int(source_boundary_blocker.sum()),
            "Out-of-scope, fabricated, or contradicted source rows across all claims",
        ),
        _metric("priority_review_row_count", len(review), "Priority-enriched review set; not random"),
        _metric("priority_review_nonempty_answer_count", int(_nonempty(review["output_text"]).sum()), "Rows with reviewable answer content"),
        _metric("priority_review_empty_answer_count", int((~_nonempty(review["output_text"])).sum()), "Reliability failures; not legal-content judgments"),
        _metric(
            "completed_final_review_rows",
            int(_completed_final_review_mask(review).sum()),
            "Rows with populated final review fields; does not recreate independent reviewer A/B labels",
        ),
        _metric(
            "reviewer_level_independent_label_rows",
            int(_reviewer_pair_mask(review).sum()),
            "Reviewer A/B raw labels are not present in the current public evidence schema",
        ),
        _metric("formal_reviewer_iaa", "not_reported", "Not reproducible without reviewer-level independent labels"),
        _metric("formal_judge_human_agreement", "not_reported", "Legacy manually aggregated summary is not published as a formal agreement statistic"),
    ]

    policy_col = next(
        (name for name in ["release_gate_decision", "release_decision"] if name in gate.columns),
        "",
    )
    if policy_col:
        for value, count in gate[policy_col].astype(str).value_counts().sort_index().items():
            rows.append(_metric(f"release_gate_{value}_count", int(count), "Group-level release-gate decision"))

    route_col = "response_policy" if "response_policy" in routing.columns else "release_decision" if "release_decision" in routing.columns else ""
    if route_col:
        for value, count in routing[route_col].astype(str).value_counts().sort_index().items():
            rows.append(_metric(f"response_policy_{value}_count", int(count), "Output-level candidate response policy"))

    return pd.DataFrame(rows)


def build_release_summary(gate: pd.DataFrame) -> pd.DataFrame:
    decision_col = next(
        (name for name in ["release_gate_decision", "release_decision"] if name in gate.columns),
        None,
    )
    if decision_col is None:
        raise SystemExit("Release gate artifact has no decision column")
    return (
        gate.groupby(decision_col, dropna=False)
        .size()
        .rename("group_count")
        .reset_index()
        .rename(columns={decision_col: "release_gate_decision"})
        .sort_values("release_gate_decision")
    )


def build_claim_summary(claims: pd.DataFrame) -> pd.DataFrame:
    reviewable = _bool_series(claims["reviewable_legal_claim"])
    grouped = (
        claims.assign(reviewable_legal_claim=reviewable)
        .groupby(["reviewable_legal_claim", "entailment_label"], dropna=False)
        .size()
        .rename("claim_count")
        .reset_index()
        .sort_values(["reviewable_legal_claim", "entailment_label"])
    )
    return grouped


def build_redacted_samples(frames: dict[str, pd.DataFrame], limit: int = 20) -> pd.DataFrame:
    runs = frames["runs"]
    candidates = runs[_nonempty(runs["output_text"])].copy()
    routing = frames["routing"]
    scores = frames["scores"]
    route_cols = [
        column
        for column in [
            "run_id",
            "response_policy",
            "workflow_status",
            "main_error_type",
            "data_asset_routes",
        ]
        if column in routing.columns
    ]
    score_cols = [
        column
        for column in ["run_id", "score_rate", "risk_level", "needs_human_review"]
        if column in scores.columns
    ]
    candidates = candidates.merge(routing[route_cols].drop_duplicates("run_id"), on="run_id", how="left")
    candidates = candidates.merge(scores[score_cols].drop_duplicates("run_id"), on="run_id", how="left")
    candidates["_policy_priority"] = candidates.get(
        "response_policy", pd.Series("", index=candidates.index)
    ).map({"block": 0, "human_review": 1, "clarify": 2, "grounded_answer": 3, "auto_answer": 4}).fillna(5)
    candidates["_score_sort"] = pd.to_numeric(
        candidates.get("score_rate", pd.Series(1.0, index=candidates.index)), errors="coerce"
    ).fillna(1.0)

    flagship_rows = []
    for sample_id in ["LPB-RISK-001", "LPB-CITE-001", "LPB-CITE-002"]:
        sample_rows = candidates[candidates["sample_id"].eq(sample_id)].sort_values(
            ["_policy_priority", "_score_sort", "model_alias", "version", "run_id"]
        )
        if not sample_rows.empty:
            flagship_rows.append(sample_rows.head(1))
    selected = pd.concat(flagship_rows, ignore_index=True) if flagship_rows else candidates.head(0)

    remaining = candidates[~candidates["run_id"].isin(selected["run_id"])].sort_values(
        ["model_alias", "version", "sample_id", "run_id"]
    )
    first_per_cell = remaining.drop_duplicates(["model_alias", "version"], keep="first")
    selected = pd.concat([selected, first_per_cell.head(limit - len(selected))], ignore_index=True)
    if len(selected) < limit:
        remaining = candidates[~candidates["run_id"].isin(selected["run_id"])]
        selected = pd.concat([selected, remaining.head(limit - len(selected))], ignore_index=True)

    rows: list[dict[str, Any]] = []
    for _, row in selected.head(limit).iterrows():
        output = str(row["output_text"])
        rows.append(
            {
                "run_id": row["run_id"],
                "sample_id": row["sample_id"],
                "model_alias": row["model_alias"],
                "version": row["version"],
                "workflow_condition": row.get("workflow_condition", ""),
                "content_status": "nonempty",
                "score_rate": row.get("score_rate", ""),
                "risk_level": row.get("risk_level", ""),
                "needs_human_review": row.get("needs_human_review", ""),
                "response_policy": row.get("response_policy", ""),
                "workflow_status": row.get("workflow_status", ""),
                "main_error_type": row.get("main_error_type", ""),
                "data_asset_routes": row.get("data_asset_routes", ""),
                "output_length": len(output),
                "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
                "redaction_note": "Full output text withheld from the public evidence package.",
            }
        )
    return pd.DataFrame(rows)


def build_manifest(source_dir: Path, output_dir: Path, frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    source_hashes = {
        filename: _sha256(source_dir / filename)
        for filename in SOURCE_FILES.values()
    }
    runs = frames["runs"]
    model_columns = [name for name in ["model_alias", "provider", "model_name"] if name in runs.columns]
    model_records = (
        runs[model_columns].drop_duplicates().sort_values(model_columns).to_dict(orient="records")
        if model_columns
        else []
    )
    created_at = runs.get("created_at", pd.Series("", index=runs.index)).astype(str)
    nonempty_created_at = created_at[created_at.str.strip().ne("")]
    dataset_path = ROOT / "data/eval_sets/legal_product_boundary_api_pilot_v1.jsonl"
    config_path = ROOT / "configs/pilots/qianfan_product_boundary_api_pilot.yaml"
    prompt_dir = ROOT / "prompts"
    return {
        "schema_version": "2.0",
        "package": "product_boundary_api_pilot_v1_lightweight_evidence",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "base_git_commit": _git_value("rev-parse", "HEAD"),
        "working_tree_state": _source_working_tree_state(),
        "working_tree_scope": "source_and_configuration_excluding_outputs",
        "purpose": "Public summaries deterministically generated from retained local Qianfan pilot artifacts; third-party recomputation requires the excluded raw artifacts.",
        "source_run": {
            "api_runs": int(len(frames["runs"])),
            "nonempty_answers": int(_nonempty(frames["runs"]["output_text"]).sum()),
            "empty_answers": int((~_nonempty(frames["runs"]["output_text"])).sum()),
            "cases": int(frames["runs"]["sample_id"].nunique()),
            "models": int(frames["runs"]["model_alias"].nunique()),
            "workflows": int(frames["runs"]["version"].nunique()),
        },
        "source_artifact_sha256": source_hashes,
        "reproducibility_inputs_sha256": {
            "dataset_jsonl": _sha256(dataset_path),
            "pilot_config": _sha256(config_path),
            "prompt_bundle": _tree_sha256(prompt_dir),
        },
        "run_window_utc": {
            "first_created_at": nonempty_created_at.min() if not nonempty_created_at.empty else "unknown",
            "last_created_at": nonempty_created_at.max() if not nonempty_created_at.empty else "unknown",
        },
        "provider_model_records": model_records,
        "methodology_caveats": [
            "API run count is reported separately from non-empty answer count.",
            "Empty answers are reliability failures and are excluded from legal-content quality interpretation.",
            "Judge metrics are automated baseline signals, not final model rankings or legal conclusions.",
            "The 80-row review set is priority-enriched and contains no public reviewer-level A/B labels.",
            "All 80 rows have populated final review fields, but those fields do not recreate independent reviewer A/B labels.",
            "Formal reviewer IAA and formal judge-human agreement are therefore not reported.",
            "Claim-level labels are deterministic review flags, not confirmed model error rates.",
            "Strict citation-defect metrics exclude partially supported claims; release-gate needs-review metrics include them.",
        ],
        "included_artifacts": [
            "README.md",
            "artifact_manifest.yaml",
            "metrics_summary.csv",
            "release_gate_summary.csv",
            "human_calibration_summary_priority_80.csv",
            "claim_entailment_summary.csv",
            "redacted_sample_outputs_20.csv",
        ],
        "excluded_artifacts": [
            "Raw answer text, judge rationales, reviewer notes, workbooks, and credentials remain local/ignored.",
        ],
        "output_dir": str(output_dir.relative_to(ROOT)) if output_dir.is_relative_to(ROOT) else str(output_dir),
    }


def build_review_evidence(review: pd.DataFrame) -> pd.DataFrame:
    has_answer = _nonempty(review["output_text"])
    reviewer_pair_rows = int(_reviewer_pair_mask(review).sum())
    return pd.DataFrame(
        [
            _metric("priority_review_row_count", len(review), "Priority-enriched review set; not random"),
            _metric("rows_with_nonempty_answer", int(has_answer.sum()), "Eligible for legal-content review"),
            _metric("rows_with_empty_answer", int((~has_answer).sum()), "Reliability failures; legal-content label is not applicable"),
            _metric(
                "completed_final_review_rows",
                int(_completed_final_review_mask(review).sum()),
                "Rows with populated final review fields; does not recreate independent reviewer A/B labels",
            ),
            _metric(
                "reviewer_level_a_b_label_rows",
                reviewer_pair_rows,
                "Rows with both independent reviewer A/B triage labels",
            ),
            _metric("formal_reviewer_iaa", "not_reported", "Requires reviewer-level independent labels"),
            _metric("formal_judge_human_agreement", "not_reported", "Legacy manually aggregated summary is not treated as a formal statistic"),
        ]
    )


def write_readme(output_dir: Path) -> None:
    content = """# Product-boundary API pilot: lightweight evidence\n\nThis package contains summaries deterministically generated from **300 retained local Qianfan API run records** across a 12-case subset, five model slots, and five workflows. Of those runs, **271 returned non-empty answer content and 29 returned empty content**. Empty responses are treated as reliability failures, not legal-content judgments.\n\n## Evidence boundary\n\n- Automated judge and claim flags are triage signals, not legal conclusions or a public model ranking.\n- The 80-row review set is priority-enriched and includes all 29 empty responses; it is not representative of all runs. All 80 rows have populated final review fields.\n- Reviewer-level independent A/B labels are not available in the public evidence schema, so the completed final fields do not support reviewer IAA or formal judge-human agreement.\n- Raw answers, detailed reviewer notes, and credentials remain local and are not committed; third parties cannot independently recompute this package without those excluded artifacts.\n\nRun `python scripts/build_api_pilot_evidence.py` to rebuild these files when the retained local raw artifacts are available.\n"""
    (output_dir / "README.md").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_PILOT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_PILOT_DIR)
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    frames = _read_sources(source_dir)

    build_metrics(frames).to_csv(output_dir / "metrics_summary.csv", index=False, encoding="utf-8-sig")
    build_release_summary(frames["release_gate"]).to_csv(
        output_dir / "release_gate_summary.csv", index=False, encoding="utf-8-sig"
    )
    build_claim_summary(frames["claims"]).to_csv(
        output_dir / "claim_entailment_summary.csv", index=False, encoding="utf-8-sig"
    )
    build_review_evidence(frames["review"]).to_csv(
        output_dir / "human_calibration_summary_priority_80.csv", index=False, encoding="utf-8-sig"
    )
    build_redacted_samples(frames).to_csv(
        output_dir / "redacted_sample_outputs_20.csv", index=False, encoding="utf-8-sig"
    )
    manifest = build_manifest(source_dir, output_dir, frames)
    (output_dir / "artifact_manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    write_readme(output_dir)
    print(json.dumps(manifest["source_run"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
