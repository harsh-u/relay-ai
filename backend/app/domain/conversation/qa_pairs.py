from backend.app.domain.conversation.message import ConversationMessage


def extract_answered_questions(
    messages: list[ConversationMessage],
) -> list[tuple[str, str]]:
    """Pair each user message with the assistant reply that directly follows it.

    A trailing, not-yet-answered user message (e.g. the one just asked) is
    naturally excluded, since nothing follows it yet.
    """

    pairs: list[tuple[str, str]] = []

    for previous, current in zip(messages, messages[1:], strict=False):
        if previous.role == "user" and current.role == "assistant":
            pairs.append((previous.text, current.text))

    return pairs
