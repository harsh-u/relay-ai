from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AnsweredQuestion:
    """A question a business has already had answered, available for reuse."""

    agent_id: str
    question: str
    answer: str
    created_at: datetime
