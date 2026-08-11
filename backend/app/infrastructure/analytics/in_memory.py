from backend.app.domain.analytics.decision_record import DecisionRecord
from backend.app.domain.analytics.repository import DecisionRepository
from backend.app.domain.analytics.summary import DecisionSummary
from backend.app.domain.inference import InferenceAction


class InMemoryDecisionRepository(DecisionRepository):
    def __init__(self) -> None:
        self._records: list[DecisionRecord] = []

    async def record(self, decision: DecisionRecord) -> None:
        self._records.append(decision)

    async def summarize(self, tenant_id: str, business_id: str) -> DecisionSummary:
        scoped = [
            record
            for record in self._records
            if record.tenant_id == tenant_id and record.business_id == business_id
        ]

        respond_by_source: dict[str, int] = {}

        for record in scoped:
            if record.action == InferenceAction.RESPOND and record.source is not None:
                respond_by_source[record.source] = respond_by_source.get(record.source, 0) + 1

        respond_count = sum(1 for r in scoped if r.action == InferenceAction.RESPOND)
        fallback_count = sum(1 for r in scoped if r.action == InferenceAction.FALLBACK)

        return DecisionSummary(
            total=len(scoped),
            respond_count=respond_count,
            fallback_count=fallback_count,
            respond_by_source=respond_by_source,
        )

    async def list_for_conversation(
        self,
        tenant_id: str,
        business_id: str,
        conversation_id: str,
    ) -> list[DecisionRecord]:
        return [
            record
            for record in self._records
            if record.tenant_id == tenant_id
            and record.business_id == business_id
            and record.conversation_id == conversation_id
        ]
