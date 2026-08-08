from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LLMMessage:
    """A single turn passed to an LLMProvider."""

    role: str
    content: str
