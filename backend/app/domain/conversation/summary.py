from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ConversationSummary:
    """A conversation's most recent activity - enough to recognize it and
    decide whether to look at its full history, without needing to already
    know its conversation_id."""

    conversation_id: str
    last_message_role: str
    last_message_text: str
    last_message_at: datetime
