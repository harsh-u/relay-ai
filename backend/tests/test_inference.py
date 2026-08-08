from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_greeting_is_answered_without_llm() -> None:
    response = client.post(
        "/v1/inference",
        json={
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


def test_repeat_request_is_recognized() -> None:
    response = client.post(
        "/v1/inference",
        json={
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


def test_repeat_request_variation_is_recognized() -> None:
    response = client.post(
        "/v1/inference",
        json={
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


def test_unknown_request_falls_back() -> None:
    response = client.post(
        "/v1/inference",
        json={
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


def test_empty_request_falls_back() -> None:
    response = client.post(
        "/v1/inference",
        json={
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


def test_repeat_request_returns_last_assistant_response() -> None:
    first_response = client.post(
        "/v1/inference",
        json={
            "business_id": "business-1",
            "conversation_id": "conversation-repeat",
            "text": "Hello",
        },
    )

    assert first_response.status_code == 200

    response = client.post(
        "/v1/inference",
        json={
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


def test_repeat_request_without_context_falls_back() -> None:
    response = client.post(
        "/v1/inference",
        json={
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


def test_conversation_state_is_isolated() -> None:
    first_response = client.post(
        "/v1/inference",
        json={
            "business_id": "business-1",
            "conversation_id": "conversation-a",
            "text": "Hello",
        },
    )

    assert first_response.status_code == 200

    response = client.post(
        "/v1/inference",
        json={
            "business_id": "business-1",
            "conversation_id": "conversation-b",
            "text": "Can you repeat that?",
        },
    )

    assert response.status_code == 200
    assert response.json()["action"] == "fallback"


def test_llm_response_can_be_used_for_repeat_request() -> None:
    conversation_id = "conversation-llm-context"

    fallback_response = client.post(
        "/v1/inference",
        json={
            "business_id": "business-1",
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
            "business_id": "business-1",
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


def test_llm_context_is_isolated_between_conversations() -> None:
    first_conversation = "conversation-llm-a"
    second_conversation = "conversation-llm-b"

    response = client.post(
        f"/v1/conversations/{first_conversation}/messages",
        json={
            "text": "This is conversation A.",
        },
    )

    assert response.status_code == 200

    repeat_response = client.post(
        "/v1/inference",
        json={
            "business_id": "business-1",
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
