from pathlib import Path

import pandas as pd

from legal_eval_harness.config import load_config
from legal_eval_harness.io_excel import find_eval_row, load_dataset
from legal_eval_harness.rag import (
    build_claim_entailment_rows,
    load_rag_corpus,
    retrieve_contexts,
    verify_output_citations,
)
from legal_eval_harness.runner import run_models


ROOT = Path(__file__).resolve().parents[1]


def test_rag_corpus_retrieves_expected_contract_sources():
    bundle = load_dataset(ROOT / "data/product_boundary_pilot/dataset_manifest.yaml")
    eval_row = find_eval_row(bundle, "LPB-CITE-003")
    corpus = load_rag_corpus(ROOT / "data/rag_corpus/legal_sources.csv")

    contexts = retrieve_contexts(eval_row=eval_row, corpus=corpus, top_k=4)
    source_ids = {context["source_id"] for context in contexts}

    assert {"CONTRACT-DELIVERY-001", "CONTRACT-PAY-001"}.issubset(source_ids)


def test_citation_verifier_flags_fabricated_source_id():
    contexts = [{"source_id": "CONTRACT-PAY-001"}]
    row = {
        "run_id": "RUN-1",
        "sample_id": "LPB-CITE-003",
        "model_alias": "Model_A",
        "version": "V4",
        "workflow_condition": "W2",
    }

    result = verify_output_citations(
        run_row=row,
        contexts=contexts,
        output_text="依据 [CONTRACT-PAY-001]，但还引用 [FAKE-LAW-999]。",
    )

    assert result["citation_fidelity_label"] == "fabricated_citation"
    assert result["fabricated_citation_count"] == 1


def test_claim_entailment_flags_supported_and_source_boundary():
    run_row = {
        "run_id": "RUN-1",
        "sample_id": "LPB-CITE-002",
        "model_alias": "Model_A",
        "version": "V4",
        "workflow_condition": "W2",
    }
    contexts = [
        {"source_id": "POLICY-001", "text": "员工手册第12条：一个自然月内迟到三次，部门负责人可给予书面警告。"},
        {"source_id": "STAT-LABOR-001", "text": "劳动合同解除需核验规章制度、公示告知和申辩程序。"},
    ]

    rows = build_claim_entailment_rows(
        run_row=run_row,
        contexts=contexts,
        output_text="根据 [POLICY-001]，迟到三次可给予书面警告。根据 [STAT-LABOR-001]，还需要核验解除程序。",
        allowed_source_ids=["POLICY-001"],
    )

    labels = {row["entailment_label"] for row in rows}
    assert "supported" in labels
    assert "out_of_scope_source" in labels
    assert any(row["product_action"] == "source_boundary_regression" for row in rows)


def test_claim_entailment_flags_uncited_reviewable_claim():
    run_row = {
        "run_id": "RUN-2",
        "sample_id": "LPB-CITE-001",
        "model_alias": "Model_A",
        "version": "V4",
        "workflow_condition": "W2",
    }
    rows = build_claim_entailment_rows(
        run_row=run_row,
        contexts=[{"source_id": "CONTRACT-001", "text": "逾期发货的，每逾期一日按订单价款的0.5%支付违约金。"}],
        output_text="消费者可以要求三倍赔偿。",
        allowed_source_ids=["CONTRACT-001"],
    )

    assert rows[0]["entailment_label"] == "no_citation"
    assert rows[0]["product_action"] == "human_review_and_prompt_fix"


def test_run_models_writes_rag_component_logs(tmp_path):
    config = load_config(ROOT / "config.qianfan_product_boundary_runnable.yaml")
    config["models"] = [config["models"][0]]
    config["run_plan"] = {
        "full_samples": ["LPB-CITE-003"],
        "full_versions": ["V4"],
        "deep_samples": [],
    }
    bundle = load_dataset(ROOT / "data/product_boundary_pilot/dataset_manifest.yaml")

    runs = run_models(
        bundle=bundle,
        config=config,
        mode="mock",
        output_path=tmp_path / "model_run_log.csv",
        prompt_dir=ROOT / "prompts",
    )

    retrieval = pd.read_csv(tmp_path / "retrieval_log.csv")
    citations = pd.read_csv(tmp_path / "citation_verification.csv")
    contexts = pd.read_csv(tmp_path / "rag_contexts.csv")
    assert len(runs) == 1
    assert len(retrieval) == 1
    assert len(citations) == 1
    assert not contexts.empty
    assert citations["valid_citation_count"].item() > 0
    assert citations["citation_fidelity_label"].item() in {"citation_supported", "unsupported_claim"}
    assert citations["claim_count"].item() > 0
    assert citations["claim_checks"].item()
