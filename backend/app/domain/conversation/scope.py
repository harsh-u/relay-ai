from dataclasses import dataclass


@dataclass(frozen=True)
class ConversationScope:
    tenant_id: str
    business_id: str
    conversation_id: str

    @property
    def key(self) -> str:
        return f"{self.tenant_id}:{self.business_id}:{self.conversation_id}"
