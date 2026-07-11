#!/usr/bin/env python3
"""Migrate case-bank route fields to the canonical workflow/asset taxonomy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROUTE_MAP = {
    "eval_holdout": "eval",
    "eval": "eval",
    "sft_candidate": "sft",
    "sft": "sft",
    "preference_pair": "preference",
    "preference": "preference",
    "badcase": "badcase",
    "regression_eval": "regression",
    "regression": "regression",
}
ASSET_ROUTE_ORDER = ["eval", "sft", "preference", "badcase", "regression"]
TRACE_RECOMMENDATION_MAP = {
    "limited_release_with_human_review": "human_review_required",
    "human_review_required": "human_review_required",
    "human_review_required_for_document": "human_review_required",
    "human_review_required_if_user_persists": "human_review_required",
    "candidate_limited_auto_answer": "candidate_limited_release",
    "candidate_limited_release": "candidate_limited_release",
    "blocked_if_fabrication_requested": "blocked",
    "blocked": "blocked",
}


def _asset_routes(values: Any) -> list[str]:
    mapped = {
        ASSET_ROUTE_MAP[str(value)]
        for value in values or []
        if str(value) in ASSET_ROUTE_MAP
    }
    return [value for value in ASSET_ROUTE_ORDER if value in mapped]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def migrate_product_boundary(path: Path) -> int:
    rows = _read_jsonl(path)
    changed = 0
    for row in rows:
        legacy = row.pop("expected_data_route", None)
        current = row.get("expected_data_asset_routes")
        routes = _asset_routes(current if current is not None else legacy)
        if row.get("expected_data_asset_routes") != routes or legacy is not None:
            row["expected_data_asset_routes"] = routes
            changed += 1
    _write_jsonl(path, rows)
    return changed


def migrate_a5(path: Path) -> int:
    rows = _read_jsonl(path)
    changed = 0
    for row in rows:
        before = json.dumps(row, ensure_ascii=False, sort_keys=True)
        legacy_recommendation = row.pop("expected_release_policy", None)
        if legacy_recommendation is not None and "expected_trace_review_recommendation" not in row:
            row["expected_trace_review_recommendation"] = legacy_recommendation
        recommendation = str(row.get("expected_trace_review_recommendation") or "")
        row["expected_trace_review_recommendation"] = TRACE_RECOMMENDATION_MAP.get(
            recommendation, recommendation
        )
        legacy_routes = row.pop("expected_data_route", None)
        current_routes = row.get("expected_data_asset_routes")
        routes = _asset_routes(current_routes if current_routes is not None else legacy_routes)
        row["expected_data_asset_routes"] = routes
        after = json.dumps(row, ensure_ascii=False, sort_keys=True)
        if before != after:
            changed += 1
    _write_jsonl(path, rows)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--product-boundary",
        type=Path,
        action="append",
        default=[],
        help="Product-boundary JSONL; may be supplied more than once.",
    )
    parser.add_argument(
        "--a5",
        type=Path,
        default=ROOT / "data/eval_sets/legal_agent_multiturn_intake_pilot_v1.jsonl",
    )
    args = parser.parse_args()

    product_paths = args.product_boundary or sorted(
        (ROOT / "data/eval_sets").glob("legal_product_boundary*.jsonl")
    )
    for path in product_paths:
        print(f"{path}: migrated {migrate_product_boundary(path)} product-boundary rows")
    print(f"{args.a5}: migrated {migrate_a5(args.a5)} A5 rows")


if __name__ == "__main__":
    main()
