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
from .utils import json_dumps, utc_now_iso


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
    deep_samples = run_plan.get("deep_samples") or sample_ids[:5]

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
    output_by_key: dict[tuple[str, str, str], str] = {}

    for spec in tqdm(build_run_plan(bundle, config), desc="model runs"):
        eval_row = find_eval_row(bundle, spec.sample_id)
        v0_output = output_by_key.get((spec.sample_id, spec.model_alias, "V0"), "")
        try:
            prompt, visible_fields = builder.render_agent_prompt(spec.version, eval_row, v0_output=v0_output)
            output_text = client.generate(
                prompt=prompt,
                model_config=spec.model_config,
                version=spec.version,
                sample_id=spec.sample_id,
                v0_output=v0_output,
            )
            run_status = "ok"
            error_message = ""
        except Exception as exc:  # preserve failed runs for auditability
            visible_fields = []
            output_text = ""
            run_status = "failed"
            error_message = str(exc)
        output_by_key[(spec.sample_id, spec.model_alias, spec.version)] = output_text
        rows.append(
            {
                "run_id": spec.run_id,
                "sample_id": spec.sample_id,
                "source_dataset": eval_row.get("source_dataset", ""),
                "task_category": eval_row.get("task_category", ""),
                "model_alias": spec.model_alias,
                "provider": spec.model_config.get("provider", ""),
                "model_name": spec.model_config.get("model", ""),
                "version": spec.version,
                "run_scope": spec.run_scope,
                "prompt_id": spec.version,
                "input_visible_fields": json_dumps(visible_fields),
                "output_text": output_text,
                "run_status": run_status,
                "error_message": error_message,
                "output_length": len(output_text),
                "created_at": utc_now_iso(),
            }
        )

    df = pd.DataFrame(rows)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return df
