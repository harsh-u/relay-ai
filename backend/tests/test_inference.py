from fastapi.testclient import TestClient

from backend.app.domain.matching.intent import Intent
from backend.app.infrastructure.embedding.fake import FakeEmbeddingProvider
from backend.app.infrastructure.knowledge.in_memory import InMemoryAnsweredQuestionRepository
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
        "similarity": None,
        "matched_question": None,
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
        "similarity": None,
        "matched_question": None,
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
        "similarity": None,
        "matched_question": None,
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
        "similarity": None,
        "matched_question": None,
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
        "similarity": None,
        "matched_question": None,
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
        "similarity": None,
        "matched_question": None,
    }


def test_reporting_a_repeat_request_fallback_does_not_pollute_the_knowledge_cache(
    client: TestClient,
    answered_question_repository: InMemoryAnsweredQuestionRepository,
) -> None:
    """ "Can you repeat that?" with no prior context falls back - but it's a
    recognized intent, not an unanswered business question. Reporting an
    answer for it must not cache it as if it were real business content."""

    client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-1",
            "conversation_id": "conversation-repeat-no-context",
            "text": "Can you repeat that?",
        },
    )
    report_response = client.post(
        "/v1/conversations/conversation-repeat-no-context/messages",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "business-1",
            "text": "Sure, I can repeat things in this same call.",
        },
    )

    assert report_response.json()["cached"] is False
    entries = answered_question_repository._entries.get((TENANT_ID, "business-1"), [])
    assert entries == []


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
        "similarity": None,
        "matched_question": None,
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
        "similarity": None,
        "matched_question": None,
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
        "cached": True,
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
        "similarity": None,
        "matched_question": None,
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
        "similarity": None,
        "matched_question": None,
    }


async def test_business_specific_custom_pattern_is_matched(
    client: TestClient,
    pattern_repository: InMemoryIntentPatternRepository,
) -> None:
    await pattern_repository.add_pattern(
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


async def test_business_specific_custom_pattern_is_isolated_to_its_business(
    client: TestClient,
    pattern_repository: InMemoryIntentPatternRepository,
) -> None:
    await pattern_repository.add_pattern(
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


def _ask_and_report_answer(
    client: TestClient,
    conversation_id: str,
    question: str,
    answer: str,
    tenant_id: str = TENANT_ID,
    business_id: str = BUSINESS_ID,
) -> None:
    """Ask a question that falls back, then report the LLM's answer back -
    the sequence that populates the answered-question cache for a business."""

    client.post(
        "/v1/inference",
        json={
            "tenant_id": tenant_id,
            "business_id": business_id,
            "conversation_id": conversation_id,
            "text": question,
        },
    )
    client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={"tenant_id": tenant_id, "business_id": business_id, "text": answer},
    )


def test_semantic_match_does_not_fire_within_the_same_conversation_that_created_it(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    """A conversation must never have an earlier turn of itself replayed
    back at it - real bug, found by testing a multi-turn appointment-
    booking conversation: an early-stage question ("I'd like to book an
    appointment") got cached, and a later turn in the *same* conversation
    matched back onto it after the caller had already moved past that
    point, replaying stale context (e.g. asking for a name again after it
    was already given). The same content is still fine to reuse for a
    genuinely different caller - see
    test_semantic_match_reuses_answer_across_different_conversations."""

    original_question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"
    answer = "Yes, we're in-network with Delta Dental PPO."

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    _ask_and_report_answer(client, "conversation-semantic-1", original_question, answer)

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conversation-semantic-1",
            "text": rephrased_question,
        },
    )

    assert response.status_code == 200
    assert response.json()["action"] == "fallback"


def test_repeat_that_after_a_semantic_match_repeats_the_matched_answer_not_a_stale_one(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    """A knowledge-cache hit is a real spoken turn - "repeat that" right
    after one must repeat *that* answer, not something said earlier in the
    same conversation. Regression test for a real bug: the cache-hit branch
    never saved its answer as an assistant turn, so "repeat that" leaked
    whatever the previous (unrelated) cached answer had been instead."""

    first_question = "Do you accept Delta Dental insurance?"
    first_answer = "Yes, we're in-network with Delta Dental PPO."
    second_question = "What are your hours on Saturday?"
    second_answer = "We're open 9am-2pm on Saturdays."
    rephrased_first_question = "Is Delta Dental accepted here?"

    embedding_provider.set_vector(first_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(second_question, [0.0, 1.0, 0.0])
    embedding_provider.set_vector(rephrased_first_question, [1.0, 0.0, 0.0])

    seeding_conversation_id = "conversation-repeat-after-match-seed"
    caller_conversation_id = "conversation-repeat-after-match-caller"

    # Two different questions get cached from one conversation. A second,
    # different conversation (a different caller) then rephrases the
    # first one - a genuine cross-conversation match, still allowed.
    _ask_and_report_answer(client, seeding_conversation_id, first_question, first_answer)
    _ask_and_report_answer(client, seeding_conversation_id, second_question, second_answer)

    match_response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": caller_conversation_id,
            "text": rephrased_first_question,
        },
    )
    assert match_response.json()["source"] == "knowledge:semantic_match"
    assert match_response.json()["text"] == first_answer

    repeat_response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": caller_conversation_id,
            "text": "Can you repeat that?",
        },
    )

    assert repeat_response.status_code == 200
    assert repeat_response.json()["action"] == "respond"
    assert repeat_response.json()["source"] == "conversation:last_response"
    assert repeat_response.json()["text"] == first_answer


def test_fallback_reports_the_closest_cached_similarity_when_below_threshold(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    """Even when nothing was close enough to answer from, the similarity to
    the nearest cached question is still surfaced - useful for seeing how
    close a near-miss actually was, instead of just "fallback"."""

    original_question = "Do you accept Delta Dental insurance?"
    near_miss_question = "Is my dental plan covered?"

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(near_miss_question, [0.6, 0.8, 0.0])

    # A different conversation asks the near-miss question, so the cached
    # question is a genuine cross-conversation candidate rather than being
    # excluded as a same-conversation self-match.
    _ask_and_report_answer(
        client,
        "conversation-near-miss-seed",
        original_question,
        "Yes, we're in-network with Delta Dental PPO.",
    )

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conversation-near-miss-caller",
            "text": near_miss_question,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "action": "fallback",
        "text": None,
        "source": None,
        "intent": None,
        "similarity": 0.6,
        "matched_question": original_question,
    }


def test_semantic_match_does_not_fire_for_dissimilar_question(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    original_question = "Do you accept Delta Dental insurance?"
    unrelated_question = "What time do you close on Saturdays?"

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(unrelated_question, [0.0, 1.0, 0.0])

    _ask_and_report_answer(
        client,
        "conversation-semantic-2",
        original_question,
        "Yes, we're in-network with Delta Dental PPO.",
    )

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": BUSINESS_ID,
            "conversation_id": "conversation-semantic-2",
            "text": unrelated_question,
        },
    )

    assert response.status_code == 200
    assert response.json()["action"] == "fallback"


def test_semantic_match_reuses_answer_across_different_conversations(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    """The whole point: a *different* caller, in a *different* conversation,
    asking a reworded version of a question this business already answered,
    should not need another LLM call either."""

    original_question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"
    answer = "Yes, we're in-network with Delta Dental PPO."

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    _ask_and_report_answer(client, "conversation-semantic-a", original_question, answer)

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
    assert response.json() == {
        "action": "respond",
        "text": answer,
        "source": "knowledge:semantic_match",
        "intent": None,
        "similarity": 1.0,
        "matched_question": original_question,
    }


def test_semantic_match_is_isolated_to_its_business(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    original_question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    _ask_and_report_answer(
        client,
        "conversation-semantic-business-a",
        original_question,
        "Yes, we're in-network with Delta Dental PPO.",
    )

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": TENANT_ID,
            "business_id": "some-other-business",
            "conversation_id": "conversation-semantic-business-b",
            "text": rephrased_question,
        },
    )

    assert response.status_code == 200
    assert response.json()["action"] == "fallback"


def test_semantic_match_is_isolated_to_its_tenant(
    client: TestClient,
    embedding_provider: FakeEmbeddingProvider,
) -> None:
    original_question = "Do you accept Delta Dental insurance?"
    rephrased_question = "Is Delta Dental accepted here?"
    other_tenant_id = "00000000-0000-0000-0000-000000000099"

    embedding_provider.set_vector(original_question, [1.0, 0.0, 0.0])
    embedding_provider.set_vector(rephrased_question, [1.0, 0.0, 0.0])

    _ask_and_report_answer(
        client,
        "conversation-semantic-tenant-a",
        original_question,
        "Yes, we're in-network with Delta Dental PPO.",
    )

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": other_tenant_id,
            "business_id": BUSINESS_ID,
            "conversation_id": "conversation-semantic-tenant-b",
            "text": rephrased_question,
        },
    )

    assert response.status_code == 200
    assert response.json()["action"] == "fallback"
