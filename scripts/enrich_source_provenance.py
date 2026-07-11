#!/usr/bin/env python3
"""Add explicit provenance boundaries to the controlled RAG fixture corpus."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data/rag_corpus/legal_sources.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()

    frame = pd.read_csv(args.input).fillna("")
    self_authored = frame["source_url"].astype(str).eq("self_authored")
    frame["provenance_status"] = self_authored.map(
        {True: "self_authored_fixture", False: "summary_requires_primary_source_verification"}
    )
    frame["document_identifier"] = ""
    frame["source_version"] = "pilot_v1"
    frame["retrieved_at"] = ""
    frame["content_sha256"] = frame["text"].astype(str).map(
        lambda value: hashlib.sha256(value.strip().encode("utf-8")).hexdigest()
    )
    frame["license_or_origin"] = self_authored.map(
        {
            True: "self-authored synthetic evaluation fixture",
            False: "official-portal reference; exact document and reuse terms not recorded",
        }
    )
    frame["publishable_as_authoritative_source"] = False
    frame.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(
        f"Wrote {len(frame)} rows; "
        f"self-authored={int(self_authored.sum())}, "
        f"requires-primary-verification={int((~self_authored).sum())}"
    )


if __name__ == "__main__":
    main()
