from fastapi.testclient import TestClient

TENANT_ID = "00000000-0000-0000-0000-000000000001"
BUSINESS_ID = "00000000-0000-0000-0000-000000000002"
AUTH_HEADERS = {"Authorization": f"Bearer test:{TENANT_ID}"}


def test_analytics_summary_reflects_recorded_decisions(client: TestClient) -> None:
    client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "analytics-1",
            "text": "Hi",
        },
        headers=AUTH_HEADERS,
    )
    client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "analytics-2",
            "text": "What is your refund policy?",
        },
        headers=AUTH_HEADERS,
    )

    response = client.get(
        "/v1/analytics/summary",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": 2,
        "respond_count": 1,
        "fallback_count": 1,
        "avoided_llm_rate": 0.5,
        "respond_by_source": {"builtin:greeting": 1},
    }


def test_analytics_summary_is_empty_for_unseen_business(client: TestClient) -> None:
    response = client.get(
        "/v1/analytics/summary",
        params={"tenant_id": TENANT_ID, "business_id": "never-queried-business"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "respond_count": 0,
        "fallback_count": 0,
        "avoided_llm_rate": 0.0,
        "respond_by_source": {},
    }
