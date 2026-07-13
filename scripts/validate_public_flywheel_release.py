from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE = ROOT / "release/legal_flywheel_v0.1.0"
FORBIDDEN_PUBLIC_COLUMNS = {
    "output_text",
    "prompt_hash",
    "output_text_hash",
    "rerun_id",
    "baseline_run_id",
    "source_snapshot",
    "expert_override_reason",
}
PII_PATTERNS = [
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(release: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = release / "public_manifest.yaml"
    if not manifest_path.exists():
        return ["missing public_manifest.yaml"]
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    for name, metadata in (manifest.get("files") or {}).items():
        path = release / name
        if not path.exists():
            errors.append(f"missing {name}")
        elif sha256(path) != metadata.get("sha256"):
            errors.append(f"hash mismatch: {name}")
    samples_path = release / "public_redacted_samples.jsonl"
    samples = [
        json.loads(line)
        for line in samples_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if samples_path.exists() else []
    expected_samples = int((manifest.get("counts") or {}).get("public_redacted_samples", 0))
    if not 1 <= len(samples) <= 3 or len(samples) != expected_samples:
        errors.append(
            f"public sample count mismatch: files={len(samples)}, manifest={expected_samples}"
        )
    public_text = json.dumps(samples, ensure_ascii=False)
    if any(pattern.search(public_text) for pattern in PII_PATTERNS):
        errors.append("public sample PII pattern detected")
    regression_path = release / "regression_summary.csv"
    if regression_path.exists():
        frame = pd.read_csv(regression_path)
        leaked = FORBIDDEN_PUBLIC_COLUMNS.intersection(frame.columns)
        if leaked:
            errors.append(f"restricted regression columns leaked: {sorted(leaked)}")
        if len(frame) != 5:
            errors.append(f"expected 5 regression summary rows; found {len(frame)}")
        if set(frame.get("prompt_version", [])) != {"V5"}:
            errors.append("public regression summary is not V5")
        scoring_revisions = set(frame.get("scoring_revision", []))
        manifest_scoring = (manifest.get("official_regression") or {}).get("scoring_revision")
        if len(scoring_revisions) != 1 or scoring_revisions != {manifest_scoring}:
            errors.append(
                "scoring revision mismatch between regression CSV and manifest: "
                f"{sorted(scoring_revisions)} vs {manifest_scoring}"
            )
        attempts = {int(value) for value in frame.get("rerun_attempt_number", [])}
        manifest_attempt = (manifest.get("official_regression") or {}).get("attempt")
        if len(attempts) != 1 or attempts != {manifest_attempt}:
            errors.append(
                f"attempt mismatch between regression CSV and manifest: {sorted(attempts)} vs {manifest_attempt}"
            )
        report_path = release / "metrics_report.md"
        report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
        report_attempts = {
            int(value) for value in re.findall(r"Five real attempt-(\d+) reruns", report_text)
        }
        if report_attempts != attempts:
            errors.append(
                f"attempt mismatch between report and regression CSV: {sorted(report_attempts)} vs {sorted(attempts)}"
            )
    else:
        errors.append("missing regression_summary.csv")
    split_policy = manifest.get("split_policy") or {}
    independent_test = int(split_policy.get("independent_test_assets", 0))
    evaluation_role = (manifest.get("official_regression") or {}).get("evaluation_role")
    if independent_test:
        if independent_test != 5:
            errors.append(f"independent public package must contain 5 test assets; found {independent_test}")
        if split_policy.get("cross_split_contamination_check") != "passed":
            errors.append("independent public package requires a passed contamination check")
        if evaluation_role != "independent_test":
            errors.append("independent public package has the wrong evaluation role")
    else:
        if split_policy.get("cross_split_contamination_check") != "not_applicable_no_independent_test_split":
            errors.append("bug-reproduction package requires a not-applicable contamination status")
        if evaluation_role != "same_source_bug_reproduction":
            errors.append("bug-reproduction public package has the wrong evaluation role")
    metrics_path = release / "metrics_summary.csv"
    if metrics_path.exists():
        metrics = set(pd.read_csv(metrics_path).get("metric", []))
        if "median_expert_review_elapsed_seconds" in metrics:
            errors.append("deprecated expert active-review metric remains public")
        if "median_self_reported_review_entry_seconds" not in metrics:
            errors.append("missing self-reported review-entry metric")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, default=DEFAULT_RELEASE)
    args = parser.parse_args()
    errors = validate(args.release)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Public flywheel release validation passed.")


if __name__ == "__main__":
    main()
