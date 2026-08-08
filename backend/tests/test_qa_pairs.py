from datetime import UTC, datetime

from backend.app.domain.conversation.message import ConversationMessage
from backend.app.domain.conversation.qa_pairs import extract_answered_questions


def _message(role: str, text: str) -> ConversationMessage:
    return ConversationMessage(
        conversation_id="conversation-1",
        role=role,
        text=text,
        created_at=datetime.now(UTC),
    )


def test_pairs_user_then_assistant() -> None:
    messages = [_message("user", "Hello"), _message("assistant", "Hi there!")]

    assert extract_answered_questions(messages) == [("Hello", "Hi there!")]


def test_trailing_unanswered_question_is_excluded() -> None:
    messages = [
        _message("user", "Hello"),
        _message("assistant", "Hi there!"),
        _message("user", "Do you take insurance?"),
    ]

    assert extract_answered_questions(messages) == [("Hello", "Hi there!")]


def test_consecutive_user_messages_do_not_pair_with_each_other() -> None:
    messages = [
        _message("user", "Hello"),
        _message("user", "Are you there?"),
        _message("assistant", "Yes, how can I help?"),
    ]

    assert extract_answered_questions(messages) == [
        ("Are you there?", "Yes, how can I help?"),
    ]


def test_empty_history_returns_no_pairs() -> None:
    assert extract_answered_questions([]) == []


def test_multiple_qa_pairs() -> None:
    messages = [
        _message("user", "Hello"),
        _message("assistant", "Hi there!"),
        _message("user", "Do you take insurance?"),
        _message("assistant", "Yes, Delta Dental."),
    ]

    assert extract_answered_questions(messages) == [
        ("Hello", "Hi there!"),
        ("Do you take insurance?", "Yes, Delta Dental."),
    ]
