from abc import ABC, abstractmethod

from backend.app.domain.analytics.decision_record import DecisionRecord
from backend.app.domain.analytics.summary import DecisionSummary


class DecisionRepository(ABC):
    """Records every inference decision and summarizes them per business."""

    @abstractmethod
    async def record(self, decision: DecisionRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    async def summarize(self, tenant_id: str, business_id: str) -> DecisionSummary:
        raise NotImplementedError

    @abstractmethod
    async def list_for_conversation(
        self,
        tenant_id: str,
        business_id: str,
        conversation_id: str,
    ) -> list[DecisionRecord]:
        """List every decision recorded for one conversation, oldest first -
        for reviewing how each turn was actually answered after the fact."""
        raise NotImplementedError
