from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Iterable

from .asset_schemas import AssetCandidate, DatasetMembership


def normalized_user_prompt_hash(snapshot: dict[str, Any]) -> str:
    prompt = unicodedata.normalize("NFKC", str(snapshot.get("user_prompt", ""))).lower()
    prompt = re.sub(r"\s+", "", prompt)
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest() if prompt else ""


def candidate_fingerprint(candidate: AssetCandidate) -> dict[str, str]:
    return {
        "source_case_id": candidate.source_case_id,
        "source_snapshot_id": candidate.source_snapshot_id,
        "normalized_user_prompt_hash": normalized_user_prompt_hash(candidate.source_snapshot),
        "counterfactual_family_id": str(
            candidate.source_snapshot.get("counterfactual_family_id")
            or candidate.source_snapshot.get("pair_id")
            or ""
        ),
    }


def overlapping_signals(left: AssetCandidate, right: AssetCandidate) -> list[str]:
    left_fp = candidate_fingerprint(left)
    right_fp = candidate_fingerprint(right)
    return [
        field
        for field in left_fp
        if left_fp[field] and right_fp[field] and left_fp[field] == right_fp[field]
    ]


def cross_split_contamination(
    candidates: Iterable[AssetCandidate], memberships: Iterable[DatasetMembership]
) -> list[dict[str, Any]]:
    by_id = {row.asset_id: row for row in candidates}
    active = [row for row in memberships if row.status.value == "included"]
    train = [by_id[row.asset_id] for row in active if row.split == "train" and row.asset_id in by_id]
    test = [by_id[row.asset_id] for row in active if row.split == "test" and row.asset_id in by_id]
    findings: list[dict[str, Any]] = []
    for train_asset in train:
        for test_asset in test:
            signals = overlapping_signals(train_asset, test_asset)
            if signals:
                findings.append(
                    {
                        "train_asset_id": train_asset.asset_id,
                        "test_asset_id": test_asset.asset_id,
                        "matching_signals": signals,
                    }
                )
    return findings
