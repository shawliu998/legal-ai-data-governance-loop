from legal_eval_harness.judge import normalize_judge_payload


def test_normalize_judge_payload_clips_scores_and_recomputes_total():
    payload = {
        "dimension_scores": {
            "missing_facts_awareness": 3,
            "clarification_quality": "2",
            "legal_grounding": -1,
        },
        "atomic_scores": [
            {"rubric_id": "R1", "score": 3, "max_score": 2},
            {"rubric_id": "R2", "score": "bad", "max_score": "bad"},
        ],
        "total_score": 999,
        "max_score": 999,
        "score_rate": 9,
        "error_tags": [{"coarse_error_tag": "not_allowed", "error_subtype": "x"}],
        "risk_level": "unknown",
        "judge_confidence": "unknown",
        "needs_human_review": "yes",
    }

    normalized = normalize_judge_payload(payload)

    assert normalized["dimension_scores"]["missing_facts_awareness"] == 2
    assert normalized["dimension_scores"]["legal_grounding"] == 0
    assert normalized["atomic_scores"][0]["score"] == 2
    assert normalized["total_score"] != 999
    assert 0 <= normalized["score_rate"] <= 1
    assert normalized["error_tags"][0]["coarse_error_tag"] == "needs_human_review"
    assert normalized["needs_human_review"] is True
