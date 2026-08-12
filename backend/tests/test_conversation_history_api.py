from fastapi.testclient import TestClient

from backend.app.infrastructure.embedding.fake import FakeEmbeddingProvider

TENANT_ID = "00000000-0000-0000-0000-000000000001"
BUSINESS_ID = "00000000-0000-0000-0000-000000000002"
AUTH_HEADERS = {"Authorization": f"Bearer test:{TENANT_ID}"}


def test_history_is_empty_for_an_unknown_conversation(client: TestClient) -> None:
    response = client.get(
        "/v1/conversations/never-happened/history",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {"conversation_id": "never-happened", "turns": []}


def test_history_shows_a_fallback_then_reported_answer(client: TestClient) -> None:
    conversation_id = "conversation-history-fallback"

    client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": conversation_id,
            "text": "What is your refund policy?",
        },
        headers=AUTH_HEADERS,
    )
    client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "text": "Refunds within 30 days.",
        },
        headers=AUTH_HEADERS,
    )

    response = client.get(
        f"/v1/conversations/{conversation_id}/history",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    turns = response.json()["turns"]
    assert [(t["role"], t["text"]) for t in turns] == [
        ("user", "What is your refund policy?"),
        ("assistant", "Refunds within 30 days."),
    ]
    assert turns[0]["action"] == "fallback"
    assert turns[0]["answered_by"] is None
    assert turns[1]["action"] is None
    assert turns[1]["answered_by"] == "llm_fallback"


def test_history_shows_a_semantic_match_with_similarity_and_matched_question(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    original_question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"
    answer = "Yes, we're in-network with Delta Dental PPO."

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    seeding_conversation_id = "conversation-history-semantic-seed"
    caller_conversation_id = "conversation-history-semantic-caller"

    # Seeded from one conversation; a *different* conversation (a different
    # caller) rephrases it - a genuine cross-conversation match.
    client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": seeding_conversation_id,
            "text": original_question,
        },
        headers=AUTH_HEADERS,
    )
    client.post(
        f"/v1/conversations/{seeding_conversation_id}/messages",
        json={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID, "text": answer},
        headers=AUTH_HEADERS,
    )
    client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": caller_conversation_id,
            "text": rephrased_question,
        },
        headers=AUTH_HEADERS,
    )

    response = client.get(
        f"/v1/conversations/{caller_conversation_id}/history",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
        headers=AUTH_HEADERS,
    )

    turns = response.json()["turns"]
    # user turn (matched), assistant turn (now saved too - the persistence fix)
    assert [(t["role"], t["text"]) for t in turns] == [
        ("user", rephrased_question),
        ("assistant", answer),
    ]

    matched_turn = turns[0]
    assert matched_turn["action"] == "respond"
    assert matched_turn["source"] == "knowledge:semantic_match"
    assert matched_turn["similarity"] == 1.0
    assert matched_turn["matched_question"] == original_question

    assert turns[1]["answered_by"] == "relayai"


def test_history_labels_a_builtin_greeting_reply_as_answered_by_relayai(
    client: TestClient,
) -> None:
    conversation_id = "conversation-history-greeting"

    client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": conversation_id,
            "text": "hello",
        },
        headers=AUTH_HEADERS,
    )

    response = client.get(
        f"/v1/conversations/{conversation_id}/history",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
        headers=AUTH_HEADERS,
    )

    turns = response.json()["turns"]
    assert turns[0]["role"] == "user"
    assert turns[0]["action"] == "respond"
    assert turns[0]["source"] == "builtin:greeting"
    assert turns[0]["answered_by"] is None

    assert turns[1]["role"] == "assistant"
    assert turns[1]["action"] is None
    assert turns[1]["answered_by"] == "relayai"


def test_list_conversations_is_empty_for_a_business_with_no_activity(client: TestClient) -> None:
    response = client.get(
        "/v1/conversations",
        params={"tenant_id": TENANT_ID, "business_id": "00000000-0000-0000-0000-000000000099"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {"conversations": []}


def test_list_conversations_shows_recent_activity_for_discovery(client: TestClient) -> None:
    conversation_id = "conversation-list-discovery"

    client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": conversation_id,
            "text": "What are your hours?",
        },
        headers=AUTH_HEADERS,
    )

    response = client.get(
        "/v1/conversations",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    conversations = response.json()["conversations"]
    by_id = {c["conversation_id"]: c for c in conversations}
    assert conversation_id in by_id
    assert by_id[conversation_id]["last_message_role"] == "user"
    assert by_id[conversation_id]["last_message_text"] == "What are your hours?"


def test_list_conversations_respects_the_limit(client: TestClient) -> None:
    business_id = "00000000-0000-0000-0000-000000000088"

    for i in range(3):
        client.post(
            "/v1/inference",
            json={
                "tenant_id": TENANT_ID,
                "business_id": business_id,
                "conversation_id": f"conversation-list-limit-{i}",
                "text": f"Question {i}",
            },
            headers=AUTH_HEADERS,
        )

    response = client.get(
        "/v1/conversations",
        params={"tenant_id": TENANT_ID, "business_id": business_id, "limit": 2},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert len(response.json()["conversations"]) == 2
