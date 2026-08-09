from fastapi.testclient import TestClient

TENANT_ID = "00000000-0000-0000-0000-000000000001"
BUSINESS_ID = "00000000-0000-0000-0000-000000000002"


def test_add_pattern_then_it_is_matched(client: TestClient) -> None:
    add_response = client.post(
        "/v1/patterns",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "intent": "greeting",
            "pattern": "yo",
        },
    )

    assert add_response.status_code == 200
    assert add_response.json() == {"stored": True}

    inference_response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conversation-1",
            "text": "yo",
        },
    )

    assert inference_response.json()["action"] == "respond"
    assert inference_response.json()["intent"] == "greeting"


def test_add_pattern_is_idempotent(client: TestClient) -> None:
    for _ in range(2):
        response = client.post(
            "/v1/patterns",
            json={
                "tenant_id": TENANT_ID,
                "business_id": BUSINESS_ID,
                "intent": "greeting",
                "pattern": "howdy",
            },
        )
        assert response.status_code == 200

    list_response = client.get(
        "/v1/patterns",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
    )

    matching = [p for p in list_response.json()["patterns"] if p["pattern"] == "howdy"]
    assert len(matching) == 1


def test_list_patterns_returns_only_this_businesss_custom_patterns(client: TestClient) -> None:
    client.post(
        "/v1/patterns",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "intent": "greeting",
            "pattern": "yo",
        },
    )
    client.post(
        "/v1/patterns",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "some-other-business",
            "intent": "greeting",
            "pattern": "howdy",
        },
    )

    response = client.get(
        "/v1/patterns",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
    )

    assert response.json() == {"patterns": [{"intent": "greeting", "pattern": "yo"}]}


def test_remove_pattern_removes_it_and_it_stops_matching(client: TestClient) -> None:
    client.post(
        "/v1/patterns",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "intent": "greeting",
            "pattern": "yo",
        },
    )

    remove_response = client.delete(
        "/v1/patterns",
        params={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "intent": "greeting",
            "pattern": "yo",
        },
    )

    assert remove_response.status_code == 200
    assert remove_response.json() == {"removed": True}

    inference_response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conversation-2",
            "text": "yo",
        },
    )

    assert inference_response.json()["action"] == "fallback"


def test_remove_pattern_returns_false_when_nothing_matched(client: TestClient) -> None:
    response = client.delete(
        "/v1/patterns",
        params={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "intent": "greeting",
            "pattern": "never-added",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"removed": False}


def test_remove_pattern_does_not_affect_builtin_patterns(client: TestClient) -> None:
    client.delete(
        "/v1/patterns",
        params={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "intent": "greeting",
            "pattern": "hi",
        },
    )

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conversation-3",
            "text": "hi",
        },
    )

    assert response.json()["action"] == "respond"
    assert response.json()["intent"] == "greeting"
