from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from .a5_multiturn import run_a5_multiturn_smoke, summarize_a5_trace_log, validate_a5_cases
from .asset_ai_review import adjudicate_asset, draft_correction, review_asset
from .asset_audit import (
    adjudicate_blind_v2,
    backfill_lineage_and_expert_bindings,
    run_blind_review_v2,
)
from .asset_candidate_builder import (
    build_asset_candidates,
    build_independent_regression_candidates,
    build_replacement_candidate,
)
from .asset_quality import requeue_incomplete_corrections, run_asset_qa
from .asset_service import AssetService
from .aggregator import build_executive_dashboard
from .calibration import build_human_review_sample, summarize_human_calibration
from .config import get_project_default, load_config
from .dataset_builder import build_normalized_dataset
from .dataset_release import (
    apply_expert_review_bundle,
    build_dataset_release,
    build_expert_review_bundle,
    finalize_asset,
    validate_dataset_release,
    validate_v02_review_batch,
)
from .io_excel import find_eval_row, load_dataset
from .judge import run_judge
from .judge_ensemble import run_judge_ensemble
from .practice_benchmark_importer import prepare_practice_benchmark_dataset
from .product_boundary_dataset import load_product_boundary_cases, validate_product_boundary_cases
from .product_boundary_importer import prepare_product_boundary_dataset
from .prompt_builder import PromptBuilder
from .rag import build_claim_entailment_rows, summarize_claim_entailment
from .rag_v2 import DEFAULT_RAG_V2_FOCUS_CASES, build_rag_v2_report
from .release_gate import build_release_gate
from .regression_runner import (
    register_regression_assertions_v2,
    rescore_regression_outputs_v2,
    run_asset_regressions,
)
from .runner import build_run_plan, run_models
from .router import apply_review_adjudications, route_scores
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


def _model_by_alias(config: dict, alias: str) -> dict:
    models = config.get("models") or []
    for model in models:
        if str(model.get("alias")) == alias:
            return model
    raise SystemExit(f"Unknown model alias {alias}; available: {[model.get('alias') for model in models]}")


def cmd_build_asset_candidates(args: argparse.Namespace) -> None:
    rows = build_asset_candidates(
        data_dir=args.data_dir,
        cases_path=args.cases,
        runs_path=args.runs,
        reviewed_path=args.reviewed,
        allow_same_source_bug_reproduction=args.allow_same_source_bug_reproduction,
    )
    print(f"Prepared {len(rows)} asset candidates in {args.data_dir}")


def cmd_build_replacement_candidate(args: argparse.Namespace) -> None:
    from .asset_schemas import AssetType

    row = build_replacement_candidate(
        asset_id=args.asset_id,
        asset_type=AssetType(args.asset_type),
        case_id=args.case_id,
        data_dir=args.data_dir,
        cases_path=args.cases,
        runs_path=args.runs,
        reviewed_path=args.reviewed,
    )
    print(f"Prepared replacement {row.asset_id} from {row.source_case_id}")


def cmd_build_independent_regressions(args: argparse.Namespace) -> None:
    rows = build_independent_regression_candidates(
        data_dir=args.data_dir,
        eval_input_path=args.eval_input,
        gold_labels_path=args.gold_labels,
        metadata_path=args.metadata,
        runs_path=args.runs,
        routing_path=args.routing,
    )
    print(
        "Prepared independent regression candidates: "
        + ", ".join(f"{row.asset_id}={row.source_case_id}" for row in rows)
    )


def cmd_backfill_asset_lineage(args: argparse.Namespace) -> None:
    snapshots, bindings = backfill_lineage_and_expert_bindings(
        AssetService(args.data_dir), review_round_dir=args.review_round_dir
    )
    print(f"Lineage ready: {snapshots} source snapshot versions; {bindings} new expert bindings")


def cmd_run_blind_reviews_v2(args: argparse.Namespace) -> None:
    from .llm_client import LLMClient

    config = load_config(args.config)
    service = AssetService(args.data_dir)
    client = LLMClient(config, args.mode)
    reviewer_a_model = _model_by_alias(config, args.reviewer_a_model)
    reviewer_b_model = _model_by_alias(config, args.reviewer_b_model)
    adjudicator_model = _model_by_alias(config, args.adjudicator_model)
    selected = (
        [service.candidates.get(asset_id) for asset_id in args.asset_ids]
        if args.asset_ids
        else [row for row in service.candidates.all() if row.asset_status.value == "accepted"]
    )
    if any(row is None for row in selected):
        raise SystemExit("blind-v2 asset list contains an unknown asset id")
    selected = sorted(selected, key=lambda row: row.asset_id)
    if not selected:
        raise SystemExit("blind-v2 requires at least one asset")
    for candidate in selected:
        run_blind_review_v2(
            service,
            candidate.asset_id,
            "reviewer_a",
            client=client,
            model_config=reviewer_a_model,
            raw_output_root=args.raw_output_dir,
        )
        run_blind_review_v2(
            service,
            candidate.asset_id,
            "reviewer_b",
            client=client,
            model_config=reviewer_b_model,
            raw_output_root=args.raw_output_dir,
        )
        result = adjudicate_blind_v2(
            service,
            candidate.asset_id,
            client=client,
            model_config=adjudicator_model,
            raw_output_root=args.raw_output_dir,
        )
        print(f"Blind-v2 {candidate.asset_id}: {result.status}/{result.proposed_decision}")


def cmd_draft_correction(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    service = AssetService(args.data_dir)
    correction = draft_correction(
        service,
        args.asset_id,
        client=__import__("legal_eval_harness.llm_client", fromlist=["LLMClient"]).LLMClient(config, args.mode),
        model_config=_model_by_alias(config, args.model_alias),
    )
    print(f"Stored {correction.correction_id}")


def cmd_review_asset(args: argparse.Namespace) -> None:
    from .llm_client import LLMClient

    config = load_config(args.config)
    event = review_asset(
        AssetService(args.data_dir),
        args.asset_id,
        args.role,
        client=LLMClient(config, args.mode),
        model_config=_model_by_alias(config, args.model_alias),
    )
    print(f"Stored {event.event_id}: {event.decision}")


def cmd_adjudicate_asset(args: argparse.Namespace) -> None:
    from .llm_client import LLMClient

    config = load_config(args.config)
    result = adjudicate_asset(
        AssetService(args.data_dir),
        args.asset_id,
        client=LLMClient(config, args.mode),
        model_config=_model_by_alias(config, args.model_alias),
    )
    print(f"Stored {result.adjudication_id}: {result.status} / {result.proposed_decision}")


def cmd_run_asset_qa(args: argparse.Namespace) -> None:
    result = run_asset_qa(AssetService(args.data_dir), args.asset_id)
    print(f"Stored {result.quality_check_id}: {'passed' if result.passed else 'failed'}")


def cmd_requeue_incomplete_corrections(args: argparse.Namespace) -> None:
    results = requeue_incomplete_corrections(AssetService(args.data_dir))
    if not results:
        print("No mechanically incomplete pending corrections found")
        return
    for asset_id, issues in results.items():
        print(f"Requeued {asset_id}: {'; '.join(issues)}")


def cmd_prepare_flywheel_review(args: argparse.Namespace) -> None:
    from .llm_client import LLMClient

    config = load_config(args.config)
    service = AssetService(args.data_dir)
    client = LLMClient(config, args.mode)
    correction_model = _model_by_alias(config, args.correction_model)
    reviewer_a_model = _model_by_alias(config, args.reviewer_a_model)
    reviewer_b_model = _model_by_alias(config, args.reviewer_b_model)
    adjudicator_model = _model_by_alias(config, args.adjudicator_model)
    for candidate in service.candidates.all():
        current = service.candidates.get(candidate.asset_id)
        if current and current.asset_status.value in {"accepted", "rejected"}:
            print(f"Skipped terminal {candidate.asset_id}: {current.asset_status.value}")
            continue
        if current.asset_status.value in {"proposed", "rework_required"}:
            draft_correction(service, candidate.asset_id, client=client, model_config=correction_model)
        current = service.candidates.get(candidate.asset_id)
        if current and current.asset_status.value == "correction_drafting":
            from .asset_schemas import AssetStatus

            if service.has_stored_correction_for_current_draft(candidate.asset_id):
                service.transition(
                    candidate.asset_id,
                    AssetStatus.AI_REVIEW_PENDING,
                    reason="resume after stored correction draft",
                )
            else:
                draft_correction(
                    service,
                    candidate.asset_id,
                    client=client,
                    model_config=correction_model,
                )
        correction = service.latest_correction(candidate.asset_id)
        roles = {row.review_role for row in service.current_reviews_for(candidate.asset_id)}
        if "reviewer_a" not in roles:
            review_asset(
                service, candidate.asset_id, "reviewer_a", client=client, model_config=reviewer_a_model
            )
        if "reviewer_b" not in roles:
            review_asset(
                service, candidate.asset_id, "reviewer_b", client=client, model_config=reviewer_b_model
            )
        adjudication = service.current_adjudication_for(candidate.asset_id)
        if adjudication is None:
            adjudicate_asset(service, candidate.asset_id, client=client, model_config=adjudicator_model)
        current = service.candidates.get(candidate.asset_id)
        if current and current.asset_status.value == "qa_pending":
            run_asset_qa(service, candidate.asset_id)
        print(f"Prepared {candidate.asset_id}: {service.candidates.get(candidate.asset_id).asset_status.value}")
    bundle = build_expert_review_bundle(service, args.output)
    print(f"Wrote {len(bundle)} expert review rows to {args.output}")


def cmd_build_expert_review_bundle(args: argparse.Namespace) -> None:
    df = build_expert_review_bundle(AssetService(args.data_dir), args.output)
    print(f"Wrote {len(df)} expert review rows to {args.output}")


def cmd_finalize_asset(args: argparse.Namespace) -> None:
    finalize_asset(
        AssetService(args.data_dir),
        args.asset_id,
        decision=args.decision,
        reason=args.reason,
        review_elapsed_seconds=args.review_elapsed_seconds,
        reviewer_identifier=args.reviewer_identifier,
        expert_override=args.expert_override == "yes",
    )
    print(f"Finalized {args.asset_id}: {args.decision}")


def cmd_apply_expert_review_bundle(args: argparse.Namespace) -> None:
    count = apply_expert_review_bundle(AssetService(args.data_dir), args.input)
    print(f"Applied {count} legal PhD final review decisions")


def cmd_build_dataset_release(args: argparse.Namespace) -> None:
    release = build_dataset_release(
        AssetService(args.data_dir), version=args.version, output_dir=args.output_dir or None
    )
    print(f"Built {release.dataset_release_id} with {len(release.asset_ids)} accepted assets")


def cmd_validate_dataset_release(args: argparse.Namespace) -> None:
    errors = validate_dataset_release(args.release)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Dataset release validation OK")


def cmd_validate_v02_review_batch(args: argparse.Namespace) -> None:
    errors = validate_v02_review_batch(AssetService(args.data_dir), args.input)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("v0.2 independent regression review batch validation OK")


def cmd_run_asset_regression(args: argparse.Namespace) -> None:
    from .llm_client import LLMClient

    config = load_config(args.config)
    results = run_asset_regressions(
        AssetService(args.data_dir),
        client=LLMClient(config, args.mode),
        model_config=_model_by_alias(config, args.model_alias),
        output_path=args.output,
        force=args.force,
    )
    counts = pd.Series([row.regression_status for row in results]).value_counts().to_dict()
    print(f"Wrote {len(results)} real regression reruns to {args.output}: {counts}")


def cmd_upgrade_regression_assertions_v2(args: argparse.Namespace) -> None:
    count = register_regression_assertions_v2(AssetService(args.data_dir))
    print(f"Registered {count} regression assertion v2 revisions")


def cmd_rescore_regression_v2(args: argparse.Namespace) -> None:
    results = rescore_regression_outputs_v2(AssetService(args.data_dir), output_path=args.output)
    counts = pd.Series([row.regression_status for row in results]).value_counts().to_dict()
    print(f"Rescored {len(results)} existing real reruns with scoring v2: {counts}")


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
    runs = pd.read_csv(args.runs) if args.runs else None
    df = route_scores(judge_scores=scores, runs=runs, output_path=args.output)
    print(f"Wrote {len(df)} routing decisions to {args.output}")


def cmd_apply_review_adjudications(args: argparse.Namespace) -> None:
    routing = pd.read_csv(args.routing)
    adjudications = pd.read_csv(args.adjudications)
    updated = apply_review_adjudications(
        routing=routing,
        adjudications=adjudications,
        output_path=args.output,
    )
    status_counts = updated["workflow_status"].value_counts().sort_index().to_dict()
    print(f"Wrote {len(updated)} adjudicated routing rows to {args.output}")
    print(f"Workflow statuses: {status_counts}")


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
    claim_entailment = pd.read_csv(args.claim_entailment) if args.claim_entailment else None
    df = build_release_gate(
        runs=runs,
        scores=scores,
        routing=routing,
        output_path=args.output,
        claim_entailment=claim_entailment,
    )
    print(f"Wrote {len(df)} release gate rows to {args.output}")
    decision_column = "release_gate_decision" if "release_gate_decision" in df.columns else "release_decision"
    print(df[["task_category", "model_alias", "workflow_condition", decision_column]].to_string(index=False))


def cmd_build_claim_entailment(args: argparse.Namespace) -> None:
    runs = pd.read_csv(args.runs).fillna("")
    contexts_df = pd.read_csv(args.contexts).fillna("")
    case_by_id: dict[str, dict] = {}
    if args.cases_jsonl:
        case_by_id = {str(case.get("case_id")): case for case in load_product_boundary_cases(args.cases_jsonl)}

    contexts_by_run: dict[str, list[dict]] = {}
    if not contexts_df.empty:
        contexts_by_run = {
            str(run_id): group.to_dict(orient="records") for run_id, group in contexts_df.groupby("run_id", sort=False)
        }

    rows: list[dict] = []
    for _, run in runs.iterrows():
        run_row = run.to_dict()
        run_id = str(run_row.get("run_id", ""))
        contexts = contexts_by_run.get(run_id, [])
        if args.rag_only and not contexts:
            continue
        case = case_by_id.get(str(run_row.get("sample_id", "")), {})
        rows.extend(
            build_claim_entailment_rows(
                run_row=run_row,
                contexts=contexts,
                output_text=str(run_row.get("output_text", "")),
                allowed_source_ids=case.get("allowed_sources") or [],
                provided_contexts=case.get("provided_context") or [],
            )
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(output, index=False, encoding="utf-8-sig")
    summary_path = args.summary_output or str(output.with_name(output.stem + "_summary.csv"))
    summary = summarize_claim_entailment(df, summary_path)
    print(f"Wrote {len(df)} claim entailment rows to {output}")
    print(f"Wrote claim entailment summary to {summary_path}")
    print(summary.to_string(index=False))


def cmd_merge_model_outputs(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    file_names = args.file_name or [
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
            dedupe_cols = ["run_id"]
            if "judge_model_alias" in merged.columns:
                dedupe_cols.append("judge_model_alias")
            if "judge_role" in merged.columns:
                dedupe_cols.append("judge_role")
            merged = merged.drop_duplicates(dedupe_cols).sort_values(dedupe_cols)
        elif "run_id" in merged.columns:
            merged = merged.sort_values("run_id")
        merged.to_csv(output_dir / file_name, index=False, encoding="utf-8-sig")
        print(f"Wrote {len(merged)} rows to {output_dir / file_name}")


def cmd_rag_v2_report(args: argparse.Namespace) -> None:
    result = build_rag_v2_report(
        runs_path=args.runs,
        retrieval_path=args.retrieval,
        citation_path=args.citation_verification,
        claim_entailment_path=args.claim_entailment,
        cases_jsonl=args.cases_jsonl,
        output_dir=args.output_dir,
        judge_scores_path=args.scores,
        routing_path=args.routing,
        release_gate_path=args.release_gate,
        focus_cases=_alias_filter(args.focus_case) or DEFAULT_RAG_V2_FOCUS_CASES,
        focus_versions=_alias_filter(args.version) or ["V1", "V4", "V5"],
    )
    print(f"Wrote RAG V2 focused report to {args.output_dir}")
    print(result["metrics_summary"].to_string(index=False))


def cmd_validate_a5_multiturn(args: argparse.Namespace) -> None:
    from .a5_multiturn import load_a5_cases

    cases = load_a5_cases(args.input)
    errors = validate_a5_cases(cases)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    behavior_counts = pd.Series([case["user_behavior"] for case in cases]).value_counts().sort_index().to_dict()
    domain_counts = pd.Series([case["legal_domain"] for case in cases]).value_counts().sort_index().to_dict()
    print("A5 multi-turn dataset validation OK")
    print(f"Cases: {len(cases)}")
    print(f"User behaviors: {behavior_counts}")
    print(f"Legal domains: {domain_counts}")


def cmd_run_a5_multiturn(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    a5_cfg = config.get("a5_multiturn_pilot") or config.get("a5_multiturn_smoke") or {}
    case_ids = _alias_filter(args.case_id) or a5_cfg.get("case_ids") or None
    model_aliases = _alias_filter(args.model_alias) or a5_cfg.get("model_aliases") or None
    result = run_a5_multiturn_smoke(
        cases_path=args.cases,
        config=config,
        output_dir=args.output_dir,
        mode=args.mode,
        case_ids=case_ids,
        model_aliases=model_aliases,
        raw_output_dir=args.raw_output_dir or None,
    )
    print(f"Wrote A5 multi-turn outputs to {args.output_dir}")
    print(result["trace_metrics_summary"].to_string(index=False))


def cmd_a5_report(args: argparse.Namespace) -> None:
    result = summarize_a5_trace_log(trace_log_path=args.trace_log, output_dir=args.output_dir, cases_path=args.cases)
    print(f"Wrote A5 report to {args.output_dir}")
    print(result["trace_metrics_summary"].to_string(index=False))


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
    routing = route_scores(judge_scores=scores, runs=runs, output_path=routing_path)
    dashboard = build_executive_dashboard(runs=runs, scores=scores, routing=routing, output_path=dashboard_path)
    print("Pipeline complete")
    print(f"Samples: {scores['sample_id'].nunique()}")
    print(f"Runs: {len(runs)}")
    print(f"Scores: {len(scores)}")
    print(f"Human review queue size: {(routing['response_policy'] == 'human_review').sum()}")
    print(f"Blocked response count: {(routing['response_policy'] == 'block').sum()}")
    print(f"Dashboard: {dashboard}")
    print(f"Outputs: {model_path}, {judge_path}, {routing_path}, {dashboard_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Legal AI data governance loop")
    parser.set_defaults(func=None)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--prompt-dir", default="prompts")

    sub = parser.add_subparsers(dest="command")

    asset_candidates = sub.add_parser("build-asset-candidates")
    asset_candidates.add_argument("--data-dir", default="data/flywheel")
    asset_candidates.add_argument("--cases", default="data/eval_sets/legal_product_boundary_api_pilot_v1.jsonl")
    asset_candidates.add_argument("--runs", default="outputs/product_boundary_api_pilot_v1/model_run_log.csv")
    asset_candidates.add_argument(
        "--reviewed", default="outputs/product_boundary_api_pilot_v1/human_review_priority_80_reviewed.csv"
    )
    asset_candidates.add_argument(
        "--allow-same-source-bug-reproduction",
        action="store_true",
        help="Reuse SFT sources only as disclosed bug reproductions; they are never an independent test split",
    )
    asset_candidates.set_defaults(func=cmd_build_asset_candidates)

    replacement_cmd = sub.add_parser("build-replacement-candidate")
    replacement_cmd.add_argument("--data-dir", default="data/flywheel")
    replacement_cmd.add_argument("--asset-id", required=True)
    replacement_cmd.add_argument("--asset-type", choices=["sft", "preference", "regression"], required=True)
    replacement_cmd.add_argument("--case-id", required=True)
    replacement_cmd.add_argument("--cases", default="data/eval_sets/legal_product_boundary_api_pilot_v1.jsonl")
    replacement_cmd.add_argument("--runs", default="outputs/product_boundary_api_pilot_v1/model_run_log.csv")
    replacement_cmd.add_argument(
        "--reviewed", default="outputs/product_boundary_api_pilot_v1/human_review_priority_80_reviewed.csv"
    )
    replacement_cmd.set_defaults(func=cmd_build_replacement_candidate)

    independent_regression_cmd = sub.add_parser("build-independent-regression-candidates")
    independent_regression_cmd.add_argument("--data-dir", default="data/flywheel")
    independent_regression_cmd.add_argument("--eval-input", default="data/eval_input.csv")
    independent_regression_cmd.add_argument("--gold-labels", default="data/gold_labels.csv")
    independent_regression_cmd.add_argument("--metadata", default="data/sample_metadata.csv")
    independent_regression_cmd.add_argument("--runs", default="outputs/model_run_log.csv")
    independent_regression_cmd.add_argument("--routing", default="outputs/data_routing.csv")
    independent_regression_cmd.set_defaults(func=cmd_build_independent_regressions)

    lineage_cmd = sub.add_parser("backfill-asset-lineage")
    lineage_cmd.add_argument("--data-dir", default="data/flywheel")
    lineage_cmd.add_argument("--review-round-dir", default="outputs/flywheel/review_rounds")
    lineage_cmd.set_defaults(func=cmd_backfill_asset_lineage)

    blind_v2_cmd = sub.add_parser("run-blind-reviews-v2")
    blind_v2_cmd.add_argument("--data-dir", default="data/flywheel")
    blind_v2_cmd.add_argument("--config", default="configs/pilots/qianfan_product_boundary_eval.yaml")
    blind_v2_cmd.add_argument("--mode", choices=["mock", "api"], default="api")
    blind_v2_cmd.add_argument("--reviewer-a-model", default="qianfan_qwen35_27b")
    blind_v2_cmd.add_argument("--reviewer-b-model", default="qianfan_ernie_50")
    blind_v2_cmd.add_argument("--adjudicator-model", default="qianfan_deepseek_v4_pro")
    blind_v2_cmd.add_argument("--raw-output-dir", default="outputs/flywheel/blind_reviews_v2")
    blind_v2_cmd.add_argument("--asset-ids", nargs="*", default=[])
    blind_v2_cmd.set_defaults(func=cmd_run_blind_reviews_v2)

    correction_cmd = sub.add_parser("draft-correction")
    correction_cmd.add_argument("--data-dir", default="data/flywheel")
    correction_cmd.add_argument("--asset-id", required=True)
    correction_cmd.add_argument("--config", default="configs/pilots/qianfan_product_boundary_eval.yaml")
    correction_cmd.add_argument("--model-alias", default="qianfan_deepseek_v4_pro")
    correction_cmd.add_argument("--mode", choices=["mock", "api"], default="api")
    correction_cmd.set_defaults(func=cmd_draft_correction)

    asset_review_cmd = sub.add_parser("review-asset")
    asset_review_cmd.add_argument("--data-dir", default="data/flywheel")
    asset_review_cmd.add_argument("--asset-id", required=True)
    asset_review_cmd.add_argument("--role", choices=["reviewer_a", "reviewer_b"], required=True)
    asset_review_cmd.add_argument("--config", default="configs/pilots/qianfan_product_boundary_eval.yaml")
    asset_review_cmd.add_argument("--model-alias", required=True)
    asset_review_cmd.add_argument("--mode", choices=["mock", "api"], default="api")
    asset_review_cmd.set_defaults(func=cmd_review_asset)

    asset_adjudicate_cmd = sub.add_parser("adjudicate-asset")
    asset_adjudicate_cmd.add_argument("--data-dir", default="data/flywheel")
    asset_adjudicate_cmd.add_argument("--asset-id", required=True)
    asset_adjudicate_cmd.add_argument("--config", default="configs/pilots/qianfan_product_boundary_eval.yaml")
    asset_adjudicate_cmd.add_argument("--model-alias", default="qianfan_qwen35_27b")
    asset_adjudicate_cmd.add_argument("--mode", choices=["mock", "api"], default="api")
    asset_adjudicate_cmd.set_defaults(func=cmd_adjudicate_asset)

    asset_qa_cmd = sub.add_parser("run-asset-qa")
    asset_qa_cmd.add_argument("--data-dir", default="data/flywheel")
    asset_qa_cmd.add_argument("--asset-id", required=True)
    asset_qa_cmd.set_defaults(func=cmd_run_asset_qa)

    requeue_incomplete_cmd = sub.add_parser("requeue-incomplete-corrections")
    requeue_incomplete_cmd.add_argument("--data-dir", default="data/flywheel")
    requeue_incomplete_cmd.set_defaults(func=cmd_requeue_incomplete_corrections)

    prepare_review_cmd = sub.add_parser("prepare-flywheel-review")
    prepare_review_cmd.add_argument("--data-dir", default="data/flywheel")
    prepare_review_cmd.add_argument("--config", default="configs/pilots/qianfan_product_boundary_eval.yaml")
    prepare_review_cmd.add_argument("--mode", choices=["mock", "api"], default="api")
    prepare_review_cmd.add_argument("--correction-model", default="qianfan_deepseek_v4_pro")
    prepare_review_cmd.add_argument("--reviewer-a-model", default="qianfan_qwen35_27b")
    prepare_review_cmd.add_argument("--reviewer-b-model", default="qianfan_glm_52")
    prepare_review_cmd.add_argument("--adjudicator-model", default="qianfan_deepseek_v4_pro")
    prepare_review_cmd.add_argument("--output", default="outputs/flywheel/expert_review_bundle.csv")
    prepare_review_cmd.set_defaults(func=cmd_prepare_flywheel_review)

    review_bundle_cmd = sub.add_parser("build-expert-review-bundle")
    review_bundle_cmd.add_argument("--data-dir", default="data/flywheel")
    review_bundle_cmd.add_argument("--output", default="outputs/flywheel/expert_review_bundle.csv")
    review_bundle_cmd.set_defaults(func=cmd_build_expert_review_bundle)

    finalize_cmd = sub.add_parser("finalize-asset")
    finalize_cmd.add_argument("--data-dir", default="data/flywheel")
    finalize_cmd.add_argument("--asset-id", required=True)
    finalize_cmd.add_argument(
        "--decision", choices=["accepted", "rework_required", "rejected"], required=True
    )
    finalize_cmd.add_argument("--reason", required=True)
    finalize_cmd.add_argument("--review-elapsed-seconds", type=float, required=True)
    finalize_cmd.add_argument("--reviewer-identifier", default="legal_phd")
    finalize_cmd.add_argument("--expert-override", choices=["yes", "no"], default="no")
    finalize_cmd.set_defaults(func=cmd_finalize_asset)

    apply_review_bundle_cmd = sub.add_parser("apply-expert-review-bundle")
    apply_review_bundle_cmd.add_argument("--data-dir", default="data/flywheel")
    apply_review_bundle_cmd.add_argument("--input", default="outputs/flywheel/expert_review_bundle.csv")
    apply_review_bundle_cmd.set_defaults(func=cmd_apply_expert_review_bundle)

    dataset_release_cmd = sub.add_parser("build-dataset-release")
    dataset_release_cmd.add_argument("--data-dir", default="data/flywheel")
    dataset_release_cmd.add_argument("--version", default="legal_flywheel_v0.1.0")
    dataset_release_cmd.add_argument("--output-dir", default="")
    dataset_release_cmd.set_defaults(func=cmd_build_dataset_release)

    validate_release_cmd = sub.add_parser("validate-dataset-release")
    validate_release_cmd.add_argument("--release", required=True)
    validate_release_cmd.set_defaults(func=cmd_validate_dataset_release)

    validate_v02_cmd = sub.add_parser("validate-v02-review-batch")
    validate_v02_cmd.add_argument("--data-dir", default="data/flywheel")
    validate_v02_cmd.add_argument(
        "--input", default="outputs/flywheel/v0.2_independent_regression_final_review.csv"
    )
    validate_v02_cmd.set_defaults(func=cmd_validate_v02_review_batch)

    regression_cmd = sub.add_parser("run-asset-regression")
    regression_cmd.add_argument("--data-dir", default="data/flywheel")
    regression_cmd.add_argument("--config", default="configs/pilots/qianfan_product_boundary_eval.yaml")
    regression_cmd.add_argument("--model-alias", default="qianfan_deepseek_v4_pro")
    regression_cmd.add_argument("--mode", choices=["mock", "api"], default="api")
    regression_cmd.add_argument("--force", action="store_true", help="Run a new audited attempt")
    regression_cmd.add_argument(
        "--output", default="outputs/flywheel/legal_flywheel_v0.1.0/regression_results.csv"
    )
    regression_cmd.set_defaults(func=cmd_run_asset_regression)

    assertion_v2_cmd = sub.add_parser("upgrade-regression-assertions-v2")
    assertion_v2_cmd.add_argument("--data-dir", default="data/flywheel")
    assertion_v2_cmd.set_defaults(func=cmd_upgrade_regression_assertions_v2)

    rescore_v2_cmd = sub.add_parser("rescore-regression-v2")
    rescore_v2_cmd.add_argument("--data-dir", default="data/flywheel")
    rescore_v2_cmd.add_argument(
        "--output", default="outputs/flywheel/legal_flywheel_v0.1.0/regression_results.csv"
    )
    rescore_v2_cmd.set_defaults(func=cmd_rescore_regression_v2)

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
    route_cmd.add_argument("--runs", default="", help="Optional run log supplying retrieval and content-status signals")
    route_cmd.add_argument("--output", default="outputs/data_routing.csv")
    route_cmd.set_defaults(func=cmd_route_data)

    adjudicate_cmd = sub.add_parser("apply-review-adjudications")
    adjudicate_cmd.add_argument("--routing", required=True)
    adjudicate_cmd.add_argument("--adjudications", required=True)
    adjudicate_cmd.add_argument("--output", default="outputs/data_routing_adjudicated.csv")
    adjudicate_cmd.set_defaults(func=cmd_apply_review_adjudications)

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
    release_gate.add_argument("--claim-entailment", default="")
    release_gate.add_argument("--output", default="outputs/release_gate.csv")
    release_gate.set_defaults(func=cmd_release_gate)

    claim_entailment = sub.add_parser("build-claim-entailment")
    claim_entailment.add_argument("--runs", required=True)
    claim_entailment.add_argument("--contexts", required=True)
    claim_entailment.add_argument("--cases-jsonl", default="")
    claim_entailment.add_argument("--output", default="outputs/claim_entailment.csv")
    claim_entailment.add_argument("--summary-output", default="")
    claim_entailment.add_argument("--rag-only", action="store_true")
    claim_entailment.set_defaults(func=cmd_build_claim_entailment)

    merge_outputs = sub.add_parser("merge-model-outputs")
    merge_outputs.add_argument("--input-dirs", nargs="+", required=True)
    merge_outputs.add_argument("--output-dir", required=True)
    merge_outputs.add_argument("--file-name", action="append", default=[])
    merge_outputs.set_defaults(func=cmd_merge_model_outputs)

    rag_v2_report = sub.add_parser("rag-v2-report")
    rag_v2_report.add_argument("--runs", required=True)
    rag_v2_report.add_argument("--retrieval", required=True)
    rag_v2_report.add_argument("--citation-verification", required=True)
    rag_v2_report.add_argument("--claim-entailment", required=True)
    rag_v2_report.add_argument("--cases-jsonl", default="data/eval_sets/legal_product_boundary_pilot_v1.jsonl")
    rag_v2_report.add_argument("--scores", default="")
    rag_v2_report.add_argument("--routing", default="")
    rag_v2_report.add_argument("--release-gate", default="")
    rag_v2_report.add_argument("--output-dir", default="outputs/rag_v2_focused_pilot_v1")
    rag_v2_report.add_argument("--focus-case", action="append", default=[])
    rag_v2_report.add_argument("--version", action="append", default=[])
    rag_v2_report.set_defaults(func=cmd_rag_v2_report)

    validate_a5 = sub.add_parser("validate-a5-multiturn")
    validate_a5.add_argument("--input", default="data/eval_sets/legal_agent_multiturn_intake_pilot_v1.jsonl")
    validate_a5.set_defaults(func=cmd_validate_a5_multiturn)

    run_a5 = sub.add_parser("run-a5-multiturn")
    run_a5.add_argument("--cases", default="data/eval_sets/legal_agent_multiturn_intake_pilot_v1.jsonl")
    run_a5.add_argument("--config", default="configs/pilots/qianfan_a5_multiturn_smoke.yaml")
    run_a5.add_argument("--mode", choices=["mock", "api"], default="mock")
    run_a5.add_argument("--output-dir", default="outputs/a5_multiturn_intake_smoke")
    run_a5.add_argument("--raw-output-dir", default="")
    run_a5.add_argument("--case-id", action="append", default=[])
    run_a5.add_argument("--model-alias", action="append", default=[])
    run_a5.set_defaults(func=cmd_run_a5_multiturn)

    a5_report = sub.add_parser("a5-report")
    a5_report.add_argument("--trace-log", required=True)
    a5_report.add_argument("--output-dir", default="outputs/a5_multiturn_intake_smoke")
    a5_report.add_argument("--cases", default="")
    a5_report.set_defaults(func=cmd_a5_report)

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
