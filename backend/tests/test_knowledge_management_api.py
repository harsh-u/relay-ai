from fastapi.testclient import TestClient

from backend.app.infrastructure.embedding.fake import FakeEmbeddingProvider
from backend.app.infrastructure.knowledge.in_memory import InMemoryAnsweredQuestionRepository

TENANT_ID = "00000000-0000-0000-0000-000000000001"
BUSINESS_ID = "00000000-0000-0000-0000-000000000002"


def test_get_knowledge_settings_returns_defaults_for_an_unconfigured_business(
    client: TestClient,
) -> None:
    response = client.get(
        "/v1/knowledge/settings",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
    )

    assert response.status_code == 200
    assert response.json() == {"knowledge_scope": "shared", "knowledge_ttl_days": 30}


def test_get_knowledge_settings_reflects_a_prior_update_without_changing_it(
    client: TestClient,
) -> None:
    client.patch(
        "/v1/knowledge/settings",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "knowledge_scope": "isolated",
            "knowledge_ttl_days": 14,
        },
    )

    response = client.get(
        "/v1/knowledge/settings",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
    )

    assert response.json() == {"knowledge_scope": "isolated", "knowledge_ttl_days": 14}


def test_update_knowledge_settings_changes_scope_and_ttl(client: TestClient) -> None:
    response = client.patch(
        "/v1/knowledge/settings",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "knowledge_scope": "isolated",
            "knowledge_ttl_days": 14,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"knowledge_scope": "isolated", "knowledge_ttl_days": 14}


def test_update_knowledge_settings_partial_update_leaves_other_field_alone(
    client: TestClient,
) -> None:
    client.patch(
        "/v1/knowledge/settings",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "knowledge_scope": "isolated",
            "knowledge_ttl_days": 14,
        },
    )

    response = client.patch(
        "/v1/knowledge/settings",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "knowledge_ttl_days": 7,
        },
    )

    assert response.json() == {"knowledge_scope": "isolated", "knowledge_ttl_days": 7}


def test_update_knowledge_settings_actually_affects_matching(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    original_question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    client.patch(
        "/v1/knowledge/settings",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "knowledge_scope": "isolated",
        },
    )

    client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conv-a",
            "agent_id": "agent-alpha",
            "text": original_question,
        },
    )
    client.post(
        "/v1/conversations/conv-a/messages",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "agent_id": "agent-alpha",
            "text": "Yes.",
        },
    )

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conv-b",
            "agent_id": "agent-beta",
            "text": rephrased_question,
        },
    )

    assert response.json()["action"] == "fallback"


def test_add_answered_question_seeds_cache_instantly(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"
    answer = "Yes, we're in-network with Delta Dental PPO."

    embedding_provider.set_vector(question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    seed_response = client.post(
        "/v1/knowledge/answers",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "question": question,
            "answer": answer,
        },
    )

    assert seed_response.status_code == 200
    assert seed_response.json() == {"stored": True}

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conv-seeded",
            "text": rephrased_question,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "action": "respond",
        "text": answer,
        "source": "knowledge:semantic_match",
        "intent": None,
    }


def test_reporting_near_duplicate_questions_does_not_grow_the_cache(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
    answered_question_repository: InMemoryAnsweredQuestionRepository,
) -> None:
    """Five different phrasings of the same underlying question, each
    falling back and getting reported back, should collapse into one
    cached entry instead of five near-duplicate rows."""

    phrasings_and_answers = [
        ("Do you accept Delta Dental insurance?", "Yes, we accept Delta Dental PPO."),
        ("Is Delta Dental accepted here?", "Yes, we accept Delta Dental PPO."),
        ("Do y'all take Delta Dental?", "Yes, we accept Delta Dental PPO."),
        ("I have Delta Dental, does that work here?", "Yes, we accept Delta Dental PPO."),
        ("Can I use my Delta Dental plan at your office?", "Yes, we accept Delta Dental PPO."),
    ]

    for index, (question, answer) in enumerate(phrasings_and_answers):
        embedding_provider.set_vector(question, [1.0, 0.0, 0.0])

        conversation_id = f"conv-dedup-{index}"
        client.post(
            "/v1/inference",
            json={
                "tenant_id": TENANT_ID,
                "business_id": BUSINESS_ID,
                "conversation_id": conversation_id,
                "text": question,
            },
        )
        client.post(
            f"/v1/conversations/{conversation_id}/messages",
            json={
                "tenant_id": TENANT_ID,
                "business_id": BUSINESS_ID,
                "text": answer,
            },
        )

    entries = answered_question_repository._entries[(TENANT_ID, BUSINESS_ID)]
    assert len(entries) == 1


def test_list_answered_questions_returns_a_seeded_answer(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    question = "Do you accept Delta Dental insurance?"
    answer = "Yes, we're in-network with Delta Dental PPO."
    embedding_provider.set_vector(question, [1.0, 0.0, 0.0])

    client.post(
        "/v1/knowledge/answers",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "question": question,
            "answer": answer,
        },
    )

    response = client.get(
        "/v1/knowledge/answers",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
    )

    assert response.status_code == 200
    answers = response.json()["answers"]
    assert len(answers) == 1
    assert answers[0]["question"] == question
    assert answers[0]["answer"] == answer
    assert answers[0]["agent_id"] == "default"


def test_list_answered_questions_is_empty_for_a_business_with_no_cache(
    client: TestClient,
) -> None:
    response = client.get(
        "/v1/knowledge/answers",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
    )

    assert response.status_code == 200
    assert response.json() == {"answers": []}
