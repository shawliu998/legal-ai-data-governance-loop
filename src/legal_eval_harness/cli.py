from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from .aggregator import build_executive_dashboard
from .calibration import build_human_review_sample, summarize_human_calibration
from .config import get_project_default, load_config
from .dataset_builder import build_normalized_dataset
from .io_excel import find_eval_row, load_dataset
from .judge import run_judge
from .judge_ensemble import run_judge_ensemble
from .practice_benchmark_importer import prepare_practice_benchmark_dataset
from .product_boundary_dataset import load_product_boundary_cases, validate_product_boundary_cases
from .product_boundary_importer import prepare_product_boundary_dataset
from .prompt_builder import PromptBuilder
from .release_gate import build_release_gate
from .runner import build_run_plan, run_models
from .router import route_scores
from .schemas import PROTECTED_GOLD_FIELDS, VISIBLE_INPUT_FIELDS


def _alias_filter(values: list[str] | None) -> list[str]:
    aliases: list[str] = []
    for value in values or []:
        aliases.extend(part.strip() for part in str(value).split(",") if part.strip())
    return aliases


def _filter_config_models(config: dict, aliases: list[str]) -> dict:
    if not aliases:
        return config
    requested = set(aliases)
    models = config.get("models") or []
    filtered = [model for model in models if str(model.get("alias", "")) in requested]
    found = {str(model.get("alias", "")) for model in filtered}
    missing = sorted(requested - found)
    if missing:
        available = sorted(str(model.get("alias", "")) for model in models)
        raise SystemExit(f"Unknown model alias {missing}; available aliases: {available}")
    filtered_config = dict(config)
    filtered_config["models"] = filtered
    return filtered_config


def _filter_config_run_plan(config: dict, sample_ids: list[str], versions: list[str]) -> dict:
    if not sample_ids and not versions:
        return config
    filtered_config = dict(config)
    run_plan = dict(config.get("run_plan") or {})
    if sample_ids:
        run_plan["full_samples"] = sample_ids
    if versions:
        run_plan["full_versions"] = versions
        run_plan["deep_samples"] = []
        run_plan["deep_versions"] = versions
        run_plan["deep_run_skip_existing_versions"] = versions
    filtered_config["run_plan"] = run_plan
    return filtered_config


def _load_bundle(input_path: str, config: dict) -> object:
    return load_dataset(
        input_path,
        jurisdiction=get_project_default(config, "jurisdiction", "中国大陆"),
        law_snapshot_date=get_project_default(config, "law_snapshot_date", "2026-07-07"),
        legal_advice_boundary=get_project_default(
            config, "legal_advice_boundary", "仅用于诊断评测，不构成法律咨询。"
        ),
    )


def cmd_validate(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    bundle = _load_bundle(args.input, config)
    run_count = len(build_run_plan(bundle, config))
    leaked = sorted(PROTECTED_GOLD_FIELDS.intersection(bundle.eval_input.columns))
    if leaked:
        raise SystemExit(f"Eval_Input leaked protected gold fields: {leaked}")
    print("Validation OK")
    print(f"Eval_Input columns: {list(bundle.eval_input.columns)}")
    print(f"Gold_Labels columns: {list(bundle.gold_labels.columns)}")
    print(f"Samples: {bundle.eval_input['sample_id'].nunique()}")
    print(f"Rubric rows: {len(bundle.rubric_items)}")
    if "task_category" in bundle.eval_input.columns:
        print(f"Task categories: {bundle.eval_input['task_category'].value_counts().to_dict()}")
    if "source_dataset" in bundle.eval_input.columns:
        print(f"Source datasets: {bundle.eval_input['source_dataset'].value_counts().to_dict()}")
    print(f"Planned normalized runs: {run_count}")


def cmd_prepare_data(args: argparse.Namespace) -> None:
    eval_input, gold_labels, rubric_items = build_normalized_dataset(
        input_workbook=args.input_workbook,
        output_dir=args.output_dir,
    )
    print(f"Wrote {len(eval_input)} Eval_Input rows to {Path(args.output_dir) / 'eval_input.csv'}")
    print(f"Wrote {len(gold_labels)} Gold_Labels rows to {Path(args.output_dir) / 'gold_labels.csv'}")
    print(f"Wrote {len(rubric_items)} Rubric_Items rows to {Path(args.output_dir) / 'rubric_items.csv'}")


def cmd_prepare_practice_benchmark(args: argparse.Namespace) -> None:
    paths = prepare_practice_benchmark_dataset(
        output_dir=args.output_dir,
        source_dir=args.source_dir,
        download=not args.no_download,
        case_limit=args.case_limit,
        consultation_limit=args.consultation_limit,
        document_limit=args.document_limit,
    )
    eval_rows = pd.read_csv(paths["eval_input"])
    rubric_rows = pd.read_csv(paths["rubric_items"])
    print(f"Wrote practice benchmark pilot manifest to {paths['manifest']}")
    print(f"Wrote {len(eval_rows)} Eval_Input rows to {paths['eval_input']}")
    print(f"Wrote {len(rubric_rows)} Rubric_Items rows to {paths['rubric_items']}")


def cmd_prepare_product_boundary(args: argparse.Namespace) -> None:
    paths = prepare_product_boundary_dataset(input_jsonl=args.input_jsonl, output_dir=args.output_dir)
    eval_rows = pd.read_csv(paths["eval_input"])
    rubric_rows = pd.read_csv(paths["rubric_items"])
    print(f"Wrote product-boundary manifest to {paths['manifest']}")
    print(f"Wrote {len(eval_rows)} Eval_Input rows to {paths['eval_input']}")
    print(f"Wrote {len(rubric_rows)} Rubric_Items rows to {paths['rubric_items']}")


def cmd_render_prompts(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    bundle = _load_bundle(args.input, config)
    eval_row = find_eval_row(bundle, args.sample_id)
    builder = PromptBuilder(args.prompt_dir)
    prompt, visible = builder.render_agent_prompt(
        args.version, eval_row, v0_output=args.v0_output or "[V0 output placeholder for blind review]"
    )
    print(f"Visible fields: {visible}")
    print(prompt)


def cmd_run_models(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    config = _filter_config_models(config, _alias_filter(args.model_alias))
    config = _filter_config_run_plan(config, _alias_filter(args.sample_id), _alias_filter(args.version))
    bundle = _load_bundle(args.input, config)
    df = run_models(bundle=bundle, config=config, mode=args.mode, output_path=args.output)
    print(f"Wrote {len(df)} normalized model runs to {args.output}")


def cmd_run_judge(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    bundle = _load_bundle(args.input, config)
    runs = pd.read_csv(args.runs)
    df = run_judge(runs=runs, bundle=bundle, config=config, mode=args.mode, output_path=args.output)
    print(f"Wrote {len(df)} judge scores to {args.output}")


def cmd_run_judge_ensemble(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    bundle = _load_bundle(args.input, config)
    runs = pd.read_csv(args.runs)
    result = run_judge_ensemble(
        runs=runs,
        bundle=bundle,
        config=config,
        mode=args.mode,
        output_dir=args.output_dir,
        prompt_dir=args.prompt_dir,
    )
    print(
        f"Wrote {len(result['scores'])} ensemble judge scores to "
        f"{Path(args.output_dir) / 'judge_ensemble_scores.csv'}"
    )
    print(
        f"Wrote {len(result['disagreements'])} disagreement rows to "
        f"{Path(args.output_dir) / 'judge_disagreements.csv'}"
    )
    print(
        f"Wrote {len(result['summary'])} ensemble summary rows to "
        f"{Path(args.output_dir) / 'judge_ensemble_summary.csv'}"
    )


def cmd_route_data(args: argparse.Namespace) -> None:
    scores = pd.read_csv(args.scores)
    df = route_scores(judge_scores=scores, output_path=args.output)
    print(f"Wrote {len(df)} routing decisions to {args.output}")


def cmd_summarize(args: argparse.Namespace) -> None:
    runs = pd.read_csv(args.runs)
    scores = pd.read_csv(args.scores)
    routing = pd.read_csv(args.routing)
    dashboard = build_executive_dashboard(runs=runs, scores=scores, routing=routing, output_path=args.output)
    print(f"Wrote executive dashboard to {args.output}")
    print(dashboard)


def cmd_sample_human_review(args: argparse.Namespace) -> None:
    runs = pd.read_csv(args.runs)
    scores = pd.read_csv(args.scores)
    routing = pd.read_csv(args.routing)
    citation_verification = pd.read_csv(args.citation_verification) if args.citation_verification else None
    ensemble_summary = pd.read_csv(args.ensemble_summary) if args.ensemble_summary else None
    df = build_human_review_sample(
        runs=runs,
        scores=scores,
        routing=routing,
        citation_verification=citation_verification,
        ensemble_summary=ensemble_summary,
        output_path=args.output,
        sample_rate=args.sample_rate,
        min_samples=args.min_samples,
        random_calibration_min=args.random_calibration_min,
        random_state=args.random_state,
    )
    print(f"Wrote {len(df)} human review calibration rows to {args.output}")


def cmd_summarize_human_calibration(args: argparse.Namespace) -> None:
    reviewed = pd.read_csv(args.input)
    df = summarize_human_calibration(reviewed=reviewed, output_path=args.output)
    print(f"Wrote human calibration summary to {args.output}")
    print(df.to_string(index=False))


def cmd_release_gate(args: argparse.Namespace) -> None:
    runs = pd.read_csv(args.runs)
    scores = pd.read_csv(args.scores)
    routing = pd.read_csv(args.routing)
    df = build_release_gate(runs=runs, scores=scores, routing=routing, output_path=args.output)
    print(f"Wrote {len(df)} release gate rows to {args.output}")
    print(df[["task_category", "model_alias", "workflow_condition", "release_decision"]].to_string(index=False))


def cmd_merge_model_outputs(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    file_names = [
        "model_run_log.csv",
        "retrieval_log.csv",
        "rag_contexts.csv",
        "citation_verification.csv",
    ]
    for file_name in file_names:
        frames = []
        for input_dir in args.input_dirs:
            path = Path(input_dir) / file_name
            if path.exists():
                try:
                    frames.append(pd.read_csv(path))
                except EmptyDataError:
                    continue
        if not frames:
            continue
        merged = pd.concat(frames, ignore_index=True)
        if file_name != "rag_contexts.csv" and "run_id" in merged.columns:
            merged = merged.drop_duplicates("run_id").sort_values("run_id")
        elif "run_id" in merged.columns:
            merged = merged.sort_values("run_id")
        merged.to_csv(output_dir / file_name, index=False, encoding="utf-8-sig")
        print(f"Wrote {len(merged)} rows to {output_dir / file_name}")


def cmd_validate_product_boundary(args: argparse.Namespace) -> None:
    cases = load_product_boundary_cases(args.input)
    errors = validate_product_boundary_cases(cases)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    slice_counts = pd.Series([case["slice"] for case in cases]).value_counts().sort_index().to_dict()
    print("Product boundary dataset validation OK")
    print(f"Cases: {len(cases)}")
    print(f"Slices: {slice_counts}")


def cmd_all(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(args.config)
    bundle = _load_bundle(args.input, config)
    model_path = output_dir / "model_run_log.csv"
    judge_path = output_dir / "judge_scores.csv"
    routing_path = output_dir / "data_routing.csv"
    dashboard_path = output_dir / "executive_dashboard.xlsx"

    runs = run_models(bundle=bundle, config=config, mode=args.mode, output_path=model_path)
    scores = run_judge(runs=runs, bundle=bundle, config=config, mode=args.mode, output_path=judge_path)
    routing = route_scores(judge_scores=scores, output_path=routing_path)
    dashboard = build_executive_dashboard(runs=runs, scores=scores, routing=routing, output_path=dashboard_path)
    print("Pipeline complete")
    print(f"Samples: {scores['sample_id'].nunique()}")
    print(f"Runs: {len(runs)}")
    print(f"Scores: {len(scores)}")
    print(f"Human review queue size: {(routing['data_route'] == 'human_review').sum()}")
    print(f"Dashboard: {dashboard}")
    print(f"Outputs: {model_path}, {judge_path}, {routing_path}, {dashboard_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Legal AI data-loop governance evaluation harness")
    parser.set_defaults(func=None)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--prompt-dir", default="prompts")

    sub = parser.add_subparsers(dest="command")

    prepare = sub.add_parser("prepare-data")
    prepare.add_argument("--input-workbook", default="data/Legal_AI_Data_Governance_Eval_Harness_40_Core.xlsx")
    prepare.add_argument("--output-dir", default="data")
    prepare.set_defaults(func=cmd_prepare_data)

    practice = sub.add_parser("prepare-practice-benchmark")
    practice.add_argument("--output-dir", default="data/practice_benchmark_pilot")
    practice.add_argument("--source-dir", default=None)
    practice.add_argument("--no-download", action="store_true")
    practice.add_argument("--case-limit", type=int, default=20)
    practice.add_argument("--consultation-limit", type=int, default=6)
    practice.add_argument("--document-limit", type=int, default=4)
    practice.set_defaults(func=cmd_prepare_practice_benchmark)

    product_boundary = sub.add_parser("prepare-product-boundary")
    product_boundary.add_argument("--input-jsonl", default="data/eval_sets/legal_product_boundary_pilot_v1.jsonl")
    product_boundary.add_argument("--output-dir", default="data/product_boundary_pilot")
    product_boundary.set_defaults(func=cmd_prepare_product_boundary)

    validate = sub.add_parser("validate")
    validate.add_argument("--input", required=True)
    validate.add_argument("--config", default="config.yaml")
    validate.set_defaults(func=cmd_validate)

    render = sub.add_parser("render-prompts")
    render.add_argument("--input", required=True)
    render.add_argument("--config", default="config.yaml")
    render.add_argument("--prompt-dir", default="prompts")
    render.add_argument("--sample-id", required=True)
    render.add_argument("--version", choices=["V0", "V1", "V2", "V3", "V4", "V5"], required=True)
    render.add_argument("--v0-output", default="")
    render.set_defaults(func=cmd_render_prompts)

    run_models_cmd = sub.add_parser("run-models")
    run_models_cmd.add_argument("--input", required=True)
    run_models_cmd.add_argument("--config", default="config.yaml")
    run_models_cmd.add_argument("--mode", choices=["mock", "api"], default="mock")
    run_models_cmd.add_argument("--output", default="outputs/model_run_log.csv")
    run_models_cmd.add_argument("--model-alias", action="append", default=[])
    run_models_cmd.add_argument("--sample-id", action="append", default=[])
    run_models_cmd.add_argument("--version", action="append", default=[])
    run_models_cmd.set_defaults(func=cmd_run_models)

    judge_cmd = sub.add_parser("run-judge")
    judge_cmd.add_argument("--input", required=True)
    judge_cmd.add_argument("--config", default="config.yaml")
    judge_cmd.add_argument("--runs", required=True)
    judge_cmd.add_argument("--mode", choices=["mock", "api"], default="mock")
    judge_cmd.add_argument("--output", default="outputs/judge_scores.csv")
    judge_cmd.set_defaults(func=cmd_run_judge)

    judge_ensemble_cmd = sub.add_parser("run-judge-ensemble")
    judge_ensemble_cmd.add_argument("--input", required=True)
    judge_ensemble_cmd.add_argument("--config", default="config.yaml")
    judge_ensemble_cmd.add_argument("--runs", required=True)
    judge_ensemble_cmd.add_argument("--mode", choices=["mock", "api"], default="mock")
    judge_ensemble_cmd.add_argument("--output-dir", default="outputs")
    judge_ensemble_cmd.set_defaults(func=cmd_run_judge_ensemble)

    route_cmd = sub.add_parser("route-data")
    route_cmd.add_argument("--scores", required=True)
    route_cmd.add_argument("--output", default="outputs/data_routing.csv")
    route_cmd.set_defaults(func=cmd_route_data)

    summarize = sub.add_parser("summarize")
    summarize.add_argument("--runs", required=True)
    summarize.add_argument("--scores", required=True)
    summarize.add_argument("--routing", required=True)
    summarize.add_argument("--output", default="outputs/executive_dashboard.xlsx")
    summarize.set_defaults(func=cmd_summarize)

    human_review = sub.add_parser("sample-human-review")
    human_review.add_argument("--runs", required=True)
    human_review.add_argument("--scores", required=True)
    human_review.add_argument("--routing", required=True)
    human_review.add_argument("--citation-verification", default="")
    human_review.add_argument("--ensemble-summary", default="")
    human_review.add_argument("--output", default="outputs/human_review_calibration.csv")
    human_review.add_argument("--sample-rate", type=float, default=0.2)
    human_review.add_argument("--min-samples", type=int, default=20)
    human_review.add_argument("--random-calibration-min", type=int, default=0)
    human_review.add_argument("--random-state", type=int, default=7)
    human_review.set_defaults(func=cmd_sample_human_review)

    human_summary = sub.add_parser("summarize-human-calibration")
    human_summary.add_argument("--input", required=True)
    human_summary.add_argument("--output", default="outputs/human_calibration_summary.csv")
    human_summary.set_defaults(func=cmd_summarize_human_calibration)

    release_gate = sub.add_parser("release-gate")
    release_gate.add_argument("--runs", required=True)
    release_gate.add_argument("--scores", required=True)
    release_gate.add_argument("--routing", required=True)
    release_gate.add_argument("--output", default="outputs/release_gate.csv")
    release_gate.set_defaults(func=cmd_release_gate)

    merge_outputs = sub.add_parser("merge-model-outputs")
    merge_outputs.add_argument("--input-dirs", nargs="+", required=True)
    merge_outputs.add_argument("--output-dir", required=True)
    merge_outputs.set_defaults(func=cmd_merge_model_outputs)

    boundary = sub.add_parser("validate-product-boundary")
    boundary.add_argument("--input", default="data/eval_sets/legal_product_boundary_pilot_v1.jsonl")
    boundary.set_defaults(func=cmd_validate_product_boundary)

    all_cmd = sub.add_parser("all")
    all_cmd.add_argument("--input", required=True)
    all_cmd.add_argument("--config", default="config.yaml")
    all_cmd.add_argument("--mode", choices=["mock", "api"], default="mock")
    all_cmd.add_argument("--output-dir", default="outputs")
    all_cmd.set_defaults(func=cmd_all)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.func is None:
        parser.print_help()
        raise SystemExit(2)
    for field in VISIBLE_INPUT_FIELDS:
        if field in PROTECTED_GOLD_FIELDS:
            raise AssertionError(f"Visible field is also protected: {field}")
    args.func(args)


if __name__ == "__main__":
    main()
