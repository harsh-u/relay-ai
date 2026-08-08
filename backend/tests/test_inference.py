from fastapi.testclient import TestClient

from backend.app.domain.matching.intent import Intent
from backend.app.infrastructure.embedding.fake import FakeEmbeddingProvider
from backend.app.infrastructure.matching.in_memory_patterns import (
    InMemoryIntentPatternRepository,
)

TENANT_ID = "00000000-0000-0000-0000-000000000001"
BUSINESS_ID = "00000000-0000-0000-0000-000000000002"


def test_greeting_is_answered_without_llm(client: TestClient) -> None:
    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-1",
            "conversation_id": "conversation-1",
            "text": "Hello",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "action": "respond",
        "text": "Hello! How can I help you?",
        "source": "builtin:greeting",
        "intent": "greeting",
    }


def test_repeat_request_is_recognized(client: TestClient) -> None:
    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-1",
            "conversation_id": "conversation-without-context",
            "text": "Can you repeat that?",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "action": "fallback",
        "text": None,
        "source": None,
        "intent": "repeat_request",
    }


def test_repeat_request_variation_is_recognized(client: TestClient) -> None:
    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-1",
            "conversation_id": "conversation-without-context-2",
            "text": "Could you say that again?",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "action": "fallback",
        "text": None,
        "source": None,
        "intent": "repeat_request",
    }


def test_unknown_request_falls_back(client: TestClient) -> None:
    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-1",
            "conversation_id": "conversation-1",
            "text": "What is your refund policy?",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "action": "fallback",
        "text": None,
        "source": None,
        "intent": None,
    }


def test_empty_request_falls_back(client: TestClient) -> None:
    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-1",
            "conversation_id": "conversation-1",
            "text": "   ",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "action": "fallback",
        "text": None,
        "source": None,
        "intent": None,
    }


def test_inference_requires_tenant_id(client: TestClient) -> None:
    response = client.post(
        "/v1/inference",
        json={
            "business_id": "business-1",
            "conversation_id": "conversation-1",
            "text": "Hello",
        },
    )

    assert response.status_code == 422


def test_repeat_request_returns_last_assistant_response(client: TestClient) -> None:
    first_response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-1",
            "conversation_id": "conversation-repeat",
            "text": "Hello",
        },
    )

    assert first_response.status_code == 200

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-1",
            "conversation_id": "conversation-repeat",
            "text": "Can you repeat that?",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "action": "respond",
        "text": "Hello! How can I help you?",
        "source": "conversation:last_response",
        "intent": "repeat_request",
    }


def test_repeat_request_without_context_falls_back(client: TestClient) -> None:
    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-1",
            "conversation_id": "new-conversation",
            "text": "Can you repeat that?",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "action": "fallback",
        "text": None,
        "source": None,
        "intent": "repeat_request",
    }


def test_conversation_state_is_isolated(client: TestClient) -> None:
    first_response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-1",
            "conversation_id": "conversation-a",
            "text": "Hello",
        },
    )

    assert first_response.status_code == 200

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-1",
            "conversation_id": "conversation-b",
            "text": "Can you repeat that?",
        },
    )

    assert response.status_code == 200
    assert response.json()["action"] == "fallback"


def test_tenant_isolation_for_repeat_request(client: TestClient) -> None:
    """Same business_id/conversation_id but a different tenant must not see the response."""
    other_tenant_id = "00000000-0000-0000-0000-000000000099"

    first_response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-1",
            "conversation_id": "shared-conversation-id",
            "text": "Hello",
        },
    )

    assert first_response.status_code == 200

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": other_tenant_id,
            "business_id": "business-1",
            "conversation_id": "shared-conversation-id",
            "text": "Can you repeat that?",
        },
    )

    assert response.status_code == 200
    assert response.json()["action"] == "fallback"


def test_business_isolation_for_repeat_request(client: TestClient) -> None:
    """Same tenant_id/conversation_id but a different business must not see the response."""
    first_response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-1",
            "conversation_id": "shared-conversation-id-2",
            "text": "Hello",
        },
    )

    assert first_response.status_code == 200

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-2",
            "conversation_id": "shared-conversation-id-2",
            "text": "Can you repeat that?",
        },
    )

    assert response.status_code == 200
    assert response.json()["action"] == "fallback"


def test_llm_response_can_be_used_for_repeat_request(client: TestClient) -> None:
    conversation_id = "conversation-llm-context"

    fallback_response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": conversation_id,
            "text": "What is your refund policy?",
        },
    )

    assert fallback_response.status_code == 200
    assert fallback_response.json() == {
        "action": "fallback",
        "text": None,
        "source": None,
        "intent": None,
    }

    assistant_response = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "text": "Our refund policy allows refunds within 30 days.",
        },
    )

    assert assistant_response.status_code == 200
    assert assistant_response.json() == {
        "conversation_id": conversation_id,
        "stored": True,
    }

    repeat_response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": conversation_id,
            "text": "Can you repeat that?",
        },
    )

    assert repeat_response.status_code == 200
    assert repeat_response.json() == {
        "action": "respond",
        "text": "Our refund policy allows refunds within 30 days.",
        "source": "conversation:last_response",
        "intent": "repeat_request",
    }


def test_llm_context_is_isolated_between_conversations(client: TestClient) -> None:
    first_conversation = "conversation-llm-a"
    second_conversation = "conversation-llm-b"

    response = client.post(
        f"/v1/conversations/{first_conversation}/messages",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "text": "This is conversation A.",
        },
    )

    assert response.status_code == 200

    repeat_response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": second_conversation,
            "text": "Can you repeat that?",
        },
    )

    assert repeat_response.status_code == 200
    assert repeat_response.json() == {
        "action": "fallback",
        "text": None,
        "source": None,
        "intent": "repeat_request",
    }


def test_business_specific_custom_pattern_is_matched(
    client: TestClient,
    pattern_repository: InMemoryIntentPatternRepository,
) -> None:
    pattern_repository.add_custom_pattern(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        intent=Intent.GREETING,
        pattern="yo",
    )

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conversation-custom-pattern",
            "text": "yo",
        },
    )

    assert response.status_code == 200
    assert response.json()["action"] == "respond"
    assert response.json()["intent"] == "greeting"


def test_business_specific_custom_pattern_is_isolated_to_its_business(
    client: TestClient,
    pattern_repository: InMemoryIntentPatternRepository,
) -> None:
    pattern_repository.add_custom_pattern(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        intent=Intent.GREETING,
        pattern="yo",
    )

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "some-other-business",
            "conversation_id": "conversation-custom-pattern-2",
            "text": "yo",
        },
    )

    assert response.status_code == 200
    assert response.json()["action"] == "fallback"


def test_semantic_match_reuses_answer_for_rephrased_question(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    conversation_id = "conversation-semantic-1"
    original_question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"
    answer = "Yes, we're in-network with Delta Dental PPO."

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    fallback_response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": conversation_id,
            "text": original_question,
        },
    )

    assert fallback_response.json()["action"] == "fallback"

    stored_response = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "text": answer,
        },
    )

    assert stored_response.status_code == 200

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": conversation_id,
            "text": rephrased_question,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "action": "respond",
        "text": answer,
        "source": "conversation:semantic_match",
        "intent": None,
    }


def test_semantic_match_does_not_fire_for_dissimilar_question(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    conversation_id = "conversation-semantic-2"
    original_question = "Do you accept Delta Dental insurance?"
    unrelated_question = "What time do you close on Saturdays?"

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(unrelated_question, [0.0, 1.0, 0.0])

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
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "text": "Yes, we're in-network with Delta Dental PPO.",
        },
    )

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": conversation_id,
            "text": unrelated_question,
        },
    )

    assert response.status_code == 200
    assert response.json()["action"] == "fallback"


def test_semantic_match_is_isolated_to_its_conversation(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    original_question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conversation-semantic-a",
            "text": original_question,
        },
    )
    client.post(
        "/v1/conversations/conversation-semantic-a/messages",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "text": "Yes, we're in-network with Delta Dental PPO.",
        },
    )

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conversation-semantic-b",
            "text": rephrased_question,
        },
    )

    assert response.status_code == 200
    assert response.json()["action"] == "fallback"
