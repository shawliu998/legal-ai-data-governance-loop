from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

from .config import get_models
from .io_excel import DatasetBundle, find_eval_row
from .llm_client import LLMClient
from .prompt_builder import PromptBuilder
from .rag import (
    build_context_rows,
    build_retrieval_log_row,
    inject_retrieved_context,
    load_rag_corpus,
    retrieve_contexts,
    verify_output_citations,
)
from .utils import json_dumps, safe_text, utc_now_iso


WORKFLOW_CONDITIONS = {
    "V0": ("W0", "closed-book answer"),
    "V1": ("W1", "structured legal prompt"),
    "V2": ("W2", "blind verifier/reviewer"),
    "V3": ("W3", "risk-control workflow agent"),
    "V4": ("W2", "provided-context grounded answer"),
    "V5": ("W4", "clarification-first intake agent"),
}


def normalize_run_output_statuses(runs: pd.DataFrame) -> pd.DataFrame:
    """Backfill content validity without conflating it with API completion.

    Legacy run logs used ``run_status=ok`` for both non-empty answers and empty
    provider responses.  This normalizer is intentionally deterministic so old
    evidence can be migrated without re-calling a model provider.
    """

    normalized = runs.copy()
    if "output_text" not in normalized.columns:
        normalized["output_text"] = ""
    normalized["output_text"] = normalized["output_text"].map(safe_text)
    inferred_nonempty = normalized["output_text"].map(lambda text: bool(text.strip()))

    if "run_status" not in normalized.columns:
        normalized["run_status"] = "ok"
    prior_status = normalized["run_status"].map(safe_text)
    failed = prior_status.eq("failed")

    normalized["api_call_status"] = failed.map({True: "failed", False: "completed"})
    normalized["has_nonempty_output"] = inferred_nonempty
    normalized["content_status"] = "nonempty"
    normalized.loc[~inferred_nonempty & ~failed, "content_status"] = "empty"
    normalized.loc[failed, "content_status"] = "not_available"
    normalized["run_status"] = "ok"
    normalized.loc[~inferred_nonempty & ~failed, "run_status"] = "empty_output"
    normalized.loc[failed, "run_status"] = "failed"

    if "error_message" not in normalized.columns:
        normalized["error_message"] = ""
    normalized["error_message"] = normalized["error_message"].map(safe_text)
    empty_without_reason = normalized["run_status"].eq("empty_output") & normalized["error_message"].eq("")
    normalized.loc[empty_without_reason, "error_message"] = (
        "API call completed but returned empty answer content"
    )
    return normalized


@dataclass(frozen=True)
class RunSpec:
    sample_id: str
    model_config: dict[str, Any]
    version: str
    run_scope: str

    @property
    def model_alias(self) -> str:
        return str(self.model_config["alias"])

    @property
    def run_id(self) -> str:
        return f"RUN-{self.sample_id}-{self.model_alias}-{self.version}"


def build_run_plan(bundle: DatasetBundle, config: dict[str, Any]) -> list[RunSpec]:
    models = get_models(config)
    run_plan = config.get("run_plan") or {}
    full_versions = run_plan.get("full_versions") or ["V0", "V3"]
    deep_versions = run_plan.get("deep_versions") or ["V0", "V1", "V2", "V3"]
    skip_existing = set(run_plan.get("deep_run_skip_existing_versions") or ["V0", "V3"])
    all_sample_ids = list(bundle.eval_input["sample_id"])
    full_samples = run_plan.get("full_samples", "all")
    if full_samples == "all" or full_samples is None:
        sample_ids = all_sample_ids
    else:
        sample_ids = [str(sample_id) for sample_id in full_samples]
        unknown = sorted(set(sample_ids) - set(all_sample_ids))
        if unknown:
            raise ValueError(f"full_samples contains unknown sample_id: {unknown}")
    if "deep_samples" in run_plan:
        deep_samples = run_plan.get("deep_samples") or []
    else:
        deep_samples = sample_ids[:5]

    specs: list[RunSpec] = []
    seen: set[str] = set()
    for sample_id in sample_ids:
        for model in models:
            for version in full_versions:
                spec = RunSpec(sample_id=sample_id, model_config=model, version=version, run_scope="full")
                specs.append(spec)
                seen.add(spec.run_id)

    for sample_id in deep_samples:
        if sample_id not in sample_ids:
            raise ValueError(f"deep_samples contains unknown sample_id: {sample_id}")
        for model in models:
            for version in deep_versions:
                if version in skip_existing:
                    continue
                spec = RunSpec(sample_id=sample_id, model_config=model, version=version, run_scope="deep")
                if spec.run_id not in seen:
                    specs.append(spec)
                    seen.add(spec.run_id)
    return specs


def run_models(
    *,
    bundle: DatasetBundle,
    config: dict[str, Any],
    mode: str,
    output_path: str | Path,
    prompt_dir: str | Path = "prompts",
) -> pd.DataFrame:
    builder = PromptBuilder(prompt_dir)
    client = LLMClient(config, mode=mode)
    rows: list[dict[str, Any]] = []
    retrieval_rows: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []
    citation_rows: list[dict[str, Any]] = []
    output_by_key: dict[tuple[str, str, str], str] = {}
    rag_config = config.get("rag") or {}
    rag_enabled = bool(rag_config.get("enabled", False))
    rag_versions = set(rag_config.get("retrieval_versions") or ["V3", "V4"])
    rag_corpus = None
    if rag_enabled:
        rag_corpus = load_rag_corpus(rag_config.get("corpus_path", "data/rag_corpus/legal_sources.csv"))

    for spec in tqdm(build_run_plan(bundle, config), desc="model runs"):
        eval_row = find_eval_row(bundle, spec.sample_id)
        v0_output = output_by_key.get((spec.sample_id, spec.model_alias, "V0"), "")
        workflow_condition, workflow_name = WORKFLOW_CONDITIONS.get(spec.version, (spec.version, spec.version))
        contexts: list[dict[str, Any]] = []
        try:
            prompt_eval_row = eval_row
            if rag_enabled and rag_corpus is not None and spec.version in rag_versions:
                contexts = retrieve_contexts(
                    eval_row=eval_row,
                    corpus=rag_corpus,
                    top_k=int(rag_config.get("top_k", 4)),
                    min_score=float(rag_config.get("min_score", 0.0)),
                )
                prompt_eval_row = inject_retrieved_context(eval_row, contexts)
            prompt, visible_fields = builder.render_agent_prompt(
                spec.version,
                prompt_eval_row,
                v0_output=v0_output,
            )
            output_text, call_metadata = client.generate_with_metadata(
                prompt=prompt,
                model_config=spec.model_config,
                version=spec.version,
                sample_id=spec.sample_id,
                v0_output=v0_output,
            )
            output_text = safe_text(output_text)
            api_call_status = "completed"
            has_nonempty_output = bool(output_text.strip())
            content_status = "nonempty" if has_nonempty_output else "empty"
            run_status = "ok" if has_nonempty_output else "empty_output"
            error_message = "" if has_nonempty_output else "API call completed but returned empty answer content"
        except Exception as exc:  # preserve failed runs for auditability
            visible_fields = []
            output_text = ""
            call_metadata = {
                "latency_ms": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0.0,
                "cost_currency": spec.model_config.get("cost_currency", "USD"),
                "usage_source": "failed",
            }
            api_call_status = "failed"
            content_status = "not_available"
            has_nonempty_output = False
            run_status = "failed"
            error_message = str(exc)
        output_by_key[(spec.sample_id, spec.model_alias, spec.version)] = output_text
        run_record = {
            "run_id": spec.run_id,
            "sample_id": spec.sample_id,
            "source_dataset": eval_row.get("source_dataset", ""),
            "task_category": eval_row.get("task_category", ""),
            "model_alias": spec.model_alias,
            "model_vendor": spec.model_config.get("vendor", ""),
            "model_family": spec.model_config.get("family", ""),
            "provider": spec.model_config.get("provider", ""),
            "model_name": spec.model_config.get("model", ""),
            "version": spec.version,
            "workflow_condition": workflow_condition,
            "workflow_name": workflow_name,
            "run_scope": spec.run_scope,
            "prompt_id": spec.version,
            "input_visible_fields": json_dumps(visible_fields),
            "output_text": output_text,
            "api_call_status": api_call_status,
            "content_status": content_status,
            "has_nonempty_output": has_nonempty_output,
            "run_status": run_status,
            "error_message": error_message,
            "output_length": len(output_text),
            "latency_ms": int(call_metadata.get("latency_ms", 0)),
            "input_tokens": int(call_metadata.get("input_tokens", 0)),
            "output_tokens": int(call_metadata.get("output_tokens", 0)),
            "total_tokens": int(call_metadata.get("total_tokens", 0)),
            "estimated_cost": float(call_metadata.get("estimated_cost", 0.0)),
            "cost_currency": call_metadata.get("cost_currency", "USD"),
            "usage_source": call_metadata.get("usage_source", ""),
            "rag_enabled": bool(rag_enabled and spec.version in rag_versions),
            "rag_source_ids": json_dumps([context.get("source_id", "") for context in contexts]),
            "created_at": utc_now_iso(),
        }
        rows.append(run_record)
        if rag_enabled and spec.version in rag_versions:
            retrieval_rows.append(build_retrieval_log_row(run_row=run_record, contexts=contexts, bundle=bundle))
            context_rows.extend(build_context_rows(run_row=run_record, contexts=contexts))
            citation_rows.append(
                verify_output_citations(run_row=run_record, contexts=contexts, output_text=output_text)
            )

    df = normalize_run_output_statuses(pd.DataFrame(rows))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    if rag_enabled:
        pd.DataFrame(retrieval_rows).to_csv(
            output_path.parent / "retrieval_log.csv",
            index=False,
            encoding="utf-8-sig",
        )
        pd.DataFrame(context_rows).to_csv(output_path.parent / "rag_contexts.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(citation_rows).to_csv(
            output_path.parent / "citation_verification.csv",
            index=False,
            encoding="utf-8-sig",
        )
    return df
