from fastapi.testclient import TestClient

from backend.app.domain.business.knowledge_scope import KnowledgeScope
from backend.app.domain.business.settings import BusinessKnowledgeSettings
from backend.app.infrastructure.business.in_memory import InMemoryBusinessSettingsRepository
from backend.app.infrastructure.embedding.fake import FakeEmbeddingProvider

TENANT_ID = "00000000-0000-0000-0000-000000000001"
BUSINESS_ID = "00000000-0000-0000-0000-000000000002"


def _ask_and_report(
    client: TestClient,
    conversation_id: str,
    agent_id: str,
    question: str,
    answer: str,
) -> None:
    client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": conversation_id,
            "agent_id": agent_id,
            "text": question,
        },
    )
    client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "agent_id": agent_id,
            "text": answer,
        },
    )


def test_shared_scope_lets_agents_reuse_each_others_answers(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    """Default behavior, unchanged: businesses that don't configure
    anything get shared knowledge across all their agents."""

    original_question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"
    answer = "Yes, we're in-network with Delta Dental PPO."

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    _ask_and_report(client, "conv-shared-a", "agent-alpha", original_question, answer)

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conv-shared-b",
            "agent_id": "agent-beta",
            "text": rephrased_question,
        },
    )

    assert response.json()["action"] == "respond"
    assert response.json()["source"] == "knowledge:semantic_match"
    assert response.json()["text"] == answer


def test_isolated_scope_keeps_agents_separate(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
    business_settings_repository: InMemoryBusinessSettingsRepository,
) -> None:
    business_settings_repository.set_knowledge_settings(
        TENANT_ID,
        BUSINESS_ID,
        BusinessKnowledgeSettings(knowledge_scope=KnowledgeScope.ISOLATED, knowledge_ttl_days=30),
    )

    original_question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    _ask_and_report(client, "conv-isolated-a", "agent-alpha", original_question, "Yes, in-network.")

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conv-isolated-b",
            "agent_id": "agent-beta",
            "text": rephrased_question,
        },
    )

    assert response.json()["action"] == "fallback"


def test_isolated_scope_still_lets_same_agent_reuse_its_own_answer(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
    business_settings_repository: InMemoryBusinessSettingsRepository,
) -> None:
    business_settings_repository.set_knowledge_settings(
        TENANT_ID,
        BUSINESS_ID,
        BusinessKnowledgeSettings(knowledge_scope=KnowledgeScope.ISOLATED, knowledge_ttl_days=30),
    )

    original_question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"
    answer = "Yes, in-network."

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    _ask_and_report(client, "conv-isolated-c", "agent-alpha", original_question, answer)

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conv-isolated-d",
            "agent_id": "agent-alpha",
            "text": rephrased_question,
        },
    )

    assert response.json()["action"] == "respond"
    assert response.json()["text"] == answer


def test_ttl_zero_means_cached_answers_never_reused(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
    business_settings_repository: InMemoryBusinessSettingsRepository,
) -> None:
    """TTL is a real timestamp cutoff, not just a config knob - a 0-day
    window means even an answer cached moments ago is already "too old"."""

    business_settings_repository.set_knowledge_settings(
        TENANT_ID,
        BUSINESS_ID,
        BusinessKnowledgeSettings(knowledge_scope=KnowledgeScope.SHARED, knowledge_ttl_days=0),
    )

    original_question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    _ask_and_report(client, "conv-ttl-a", "agent-alpha", original_question, "Yes.")

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conv-ttl-b",
            "agent_id": "agent-alpha",
            "text": rephrased_question,
        },
    )

    assert response.json()["action"] == "fallback"


def test_clear_cache_endpoint_removes_cached_answers(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    original_question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    _ask_and_report(client, "conv-clear-a", "agent-alpha", original_question, "Yes.")

    clear_response = client.delete(
        "/v1/knowledge/cache",
        params={"tenant_id": TENANT_ID, "business_id": BUSINESS_ID},
    )

    assert clear_response.status_code == 200
    assert clear_response.json()["deleted"] == 1

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conv-clear-b",
            "agent_id": "agent-alpha",
            "text": rephrased_question,
        },
    )

    assert response.json()["action"] == "fallback"
