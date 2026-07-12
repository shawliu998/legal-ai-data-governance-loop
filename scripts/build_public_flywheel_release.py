from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESTRICTED = ROOT / "outputs/flywheel/legal_flywheel_v0.1.0"
DEFAULT_PUBLIC = ROOT / "release/legal_flywheel_v0.1.0"
PII_PATTERNS = [
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_public_release(restricted: Path, output: Path) -> None:
    required = [
        "release_manifest.yaml",
        "metrics_summary.csv",
        "metrics_report.md",
        "public_redacted_samples.jsonl",
        "regression_results.csv",
        "regression_assertion_audit.csv",
    ]
    missing = [name for name in required if not (restricted / name).exists()]
    if missing:
        raise SystemExit(f"Restricted release is incomplete: {missing}")
    output.mkdir(parents=True, exist_ok=True)
    for path in output.iterdir():
        if path.is_file():
            path.unlink()

    shutil.copy2(restricted / "metrics_summary.csv", output / "metrics_summary.csv")
    shutil.copy2(restricted / "metrics_report.md", output / "metrics_report.md")
    shutil.copy2(
        restricted / "public_redacted_samples.jsonl", output / "public_redacted_samples.jsonl"
    )

    results = pd.read_csv(restricted / "regression_results.csv").fillna("")
    audit = pd.read_csv(restricted / "regression_assertion_audit.csv").fillna("")
    audit["matched"] = audit["matched"].astype(str).str.lower().isin({"true", "1"})
    topic_summary = (
        audit.groupby("asset_id", as_index=False)["matched"]
        .agg(required_topics_matched="sum", required_topics_total="count")
    )
    rows = results[
        [
            "asset_id",
            "model_alias",
            "prompt_version",
            "rerun_attempt_number",
            "scoring_revision",
            "regression_status",
            "failure_reason",
            "assertion_results",
        ]
    ].merge(topic_summary, on="asset_id", how="left")
    rows.to_csv(output / "regression_summary.csv", index=False, encoding="utf-8-sig")

    samples = [
        json.loads(line)
        for line in (output / "public_redacted_samples.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    text = json.dumps(samples, ensure_ascii=False)
    if any(pattern.search(text) for pattern in PII_PATTERNS):
        raise SystemExit("Public samples failed PII scan")

    restricted_manifest = yaml.safe_load(
        (restricted / "release_manifest.yaml").read_text(encoding="utf-8")
    )
    readme = """# legal_flywheel_v0.1.0 — public evidence package

This package is the intentionally limited public view of a 15-asset legal-AI data flywheel pilot.
The full restricted release contains 5 SFT, 5 preference, and 5 regression bug-reproduction assets, item-level legal-
expert submissions, source snapshots, blind-review raw outputs, and restricted model run logs.

The public package contains only:

- three redacted example assets (one per asset type);
- aggregate workflow metrics and the evidence-boundary report;
- five same-source bug-reproduction gate outcomes without raw prompts, answers, hashes, or internal rerun identifiers;
- a hash manifest describing included and deliberately excluded evidence.

The official V5/W4 attempt produced 0 passed / 5 failed under preregistered deterministic gates.
These assets reuse SFT source cases and are not an independent test split, legal-accuracy estimate,
or model leaderboard. See `metrics_report.md` for the interpretation and attempt history.

This material is diagnostic evaluation evidence, not legal advice or a production legal service.
Repository code is distributed under the project MIT License; source legal materials remain subject to
their original authority and are not republished in this public package.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")

    public_files = {}
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != "public_manifest.yaml":
            public_files[path.name] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    manifest = {
        "release_id": "legal_flywheel_v0.1.0-public",
        "source_release_id": restricted_manifest.get("dataset_release_id"),
        "source_release_manifest_sha256": sha256(restricted / "release_manifest.yaml"),
        "counts": {"restricted_accepted_assets": 15, "public_redacted_samples": len(samples)},
        "official_regression": {
            "attempt": int(results["rerun_attempt_number"].iloc[0]),
            "reruns": 5,
            "passed": int((results["regression_status"] == "passed").sum()),
            "failed": int((results["regression_status"] == "failed").sum()),
            "workflow": "V5/W4",
            "evaluation_role": "same_source_bug_reproduction",
        },
        "split_policy": restricted_manifest.get("split_policy", {}),
        "included": sorted(public_files),
        "excluded_restricted_categories": [
            "accepted_assets_full_text",
            "expert_review_submissions",
            "source_snapshot_history",
            "blind_review_raw_outputs",
            "regression_raw_prompts_and_outputs",
            "api_usage_metadata_and_internal_rerun_ids",
        ],
        "license": "MIT for repository code; evidence remains subject to stated source boundaries",
        "files": public_files,
    }
    (output / "public_manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--restricted", type=Path, default=DEFAULT_RESTRICTED)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC)
    args = parser.parse_args()
    build_public_release(args.restricted, args.output)
    print(f"Built public flywheel release at {args.output}")


if __name__ == "__main__":
    main()
