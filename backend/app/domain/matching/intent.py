from enum import StrEnum


class Intent(StrEnum):
    """Known intents RelayAI can handle without an LLM."""

    GREETING = "greeting"
    REPEAT_REQUEST = "repeat_request"
