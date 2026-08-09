from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.analytics.decision_record import DecisionRecord
from backend.app.domain.analytics.repository import DecisionRepository
from backend.app.domain.analytics.summary import DecisionSummary
from backend.app.domain.inference import InferenceAction
from backend.app.models.decision_log import DecisionLogModel


class PostgresDecisionRepository(DecisionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, decision: DecisionRecord) -> None:
        row = DecisionLogModel(
            tenant_id=UUID(decision.tenant_id),
            business_id=UUID(decision.business_id),
            conversation_id=decision.conversation_id,
            agent_id=decision.agent_id,
            action=decision.action,
            source=decision.source,
            intent=decision.intent,
            latency_ms=decision.latency_ms,
        )

        self._session.add(row)
        await self._session.flush()

    async def summarize(self, tenant_id: str, business_id: str) -> DecisionSummary:
        scope = (
            DecisionLogModel.tenant_id == UUID(tenant_id),
            DecisionLogModel.business_id == UUID(business_id),
        )

        by_action_statement = (
            select(DecisionLogModel.action, func.count())
            .where(*scope)
            .group_by(DecisionLogModel.action)
        )
        by_action = dict((await self._session.execute(by_action_statement)).all())

        by_source_statement = (
            select(DecisionLogModel.source, func.count())
            .where(*scope, DecisionLogModel.action == InferenceAction.RESPOND)
            .group_by(DecisionLogModel.source)
        )
        by_source = dict((await self._session.execute(by_source_statement)).all())

        respond_count = by_action.get(InferenceAction.RESPOND.value, 0)
        fallback_count = by_action.get(InferenceAction.FALLBACK.value, 0)

        return DecisionSummary(
            total=respond_count + fallback_count,
            respond_count=respond_count,
            fallback_count=fallback_count,
            respond_by_source={source: count for source, count in by_source.items() if source},
        )
