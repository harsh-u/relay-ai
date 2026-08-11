from fastapi.testclient import TestClient

from backend.app.infrastructure.embedding.fake import FakeEmbeddingProvider

TENANT_ID = "00000000-0000-0000-0000-000000000001"
BUSINESS_ID = "00000000-0000-0000-0000-000000000002"


def test_history_is_empty_for_an_unknown_conversation(client: TestClient) -> None:
    response = client.get(
        "/v1/conversations/never-happened/history",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
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
    )
    client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "text": "Refunds within 30 days.",
        },
    )

    response = client.get(
        f"/v1/conversations/{conversation_id}/history",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
    )

    assert response.status_code == 200
    turns = response.json()["turns"]
    assert [(t["role"], t["text"]) for t in turns] == [
        ("user", "What is your refund policy?"),
        ("assistant", "Refunds within 30 days."),
    ]
    assert turns[0]["action"] == "fallback"
    assert turns[1]["action"] is None


def test_history_shows_a_semantic_match_with_similarity_and_matched_question(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    original_question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"
    answer = "Yes, we're in-network with Delta Dental PPO."

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    conversation_id = "conversation-history-semantic"

    client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": conversation_id,
            "text": original_question,
        },
    )
    client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID, "text": answer},
    )
    client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": conversation_id,
            "text": rephrased_question,
        },
    )

    response = client.get(
        f"/v1/conversations/{conversation_id}/history",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
    )

    turns = response.json()["turns"]
    # user Q1, assistant A1 (reported), user Q2 (matched), assistant A1 (now saved too - the fix)
    assert [(t["role"], t["text"]) for t in turns] == [
        ("user", original_question),
        ("assistant", answer),
        ("user", rephrased_question),
        ("assistant", answer),
    ]

    matched_turn = turns[2]
    assert matched_turn["action"] == "respond"
    assert matched_turn["source"] == "knowledge:semantic_match"
    assert matched_turn["similarity"] == 1.0
    assert matched_turn["matched_question"] == original_question
