from pathlib import Path

import pandas as pd

from legal_eval_harness.a5_multiturn import run_a5_multiturn_smoke, validate_a5_cases, load_a5_cases


ROOT = Path(__file__).resolve().parents[1]


def test_a5_case_file_validates():
    cases = load_a5_cases(ROOT / "data/eval_sets/legal_agent_multiturn_intake_pilot_v1.jsonl")
    assert len(cases) == 8
    assert validate_a5_cases(cases) == []


def test_a5_multiturn_smoke_writes_redacted_artifacts(tmp_path):
    config = {
        "models": [
            {
                "alias": "mock_model",
                "vendor": "Mock",
                "family": "Mock",
                "provider": "mock",
                "model": "mock",
            }
        ],
        "generation": {"temperature": 0.0, "max_output_tokens": 400},
    }

    result = run_a5_multiturn_smoke(
        cases_path=ROOT / "data/eval_sets/legal_agent_multiturn_intake_pilot_v1.jsonl",
        config=config,
        output_dir=tmp_path,
        mode="mock",
        case_ids=["A5-INTAKE-001"],
        model_aliases=["mock_model"],
    )

    metrics = result["trace_metrics_summary"].set_index("metric")
    assert metrics.loc["traces", "value"] == 1
    assert metrics.loc["turns", "value"] == 3
    assert (tmp_path / "trace_log.jsonl").exists()
    redacted = pd.read_csv(tmp_path / "redacted_trace_samples.csv")
    assert "agent_message" not in redacted.columns
    assert redacted["turn_output_hashes"].item()
