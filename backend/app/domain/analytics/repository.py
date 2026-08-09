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
