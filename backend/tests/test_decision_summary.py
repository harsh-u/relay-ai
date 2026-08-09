from backend.app.domain.analytics.summary import DecisionSummary


def test_avoided_llm_rate_computes_share_of_responses() -> None:
    summary = DecisionSummary(total=4, respond_count=3, fallback_count=1)

    assert summary.avoided_llm_rate == 0.75


def test_avoided_llm_rate_is_zero_when_no_requests() -> None:
    summary = DecisionSummary(total=0, respond_count=0, fallback_count=0)

    assert summary.avoided_llm_rate == 0.0


def test_respond_by_source_defaults_to_empty() -> None:
    summary = DecisionSummary(total=1, respond_count=1, fallback_count=0)

    assert summary.respond_by_source == {}
