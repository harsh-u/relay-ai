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
            similarity=decision.similarity,
            matched_question=decision.matched_question,
            latency_ms=decision.latency_ms,
        )

        self._session.add(row)
        await self._session.flush()

    async def list_for_conversation(
        self,
        tenant_id: str,
        business_id: str,
        conversation_id: str,
    ) -> list[DecisionRecord]:
        statement = (
            select(DecisionLogModel)
            .where(
                DecisionLogModel.tenant_id == UUID(tenant_id),
                DecisionLogModel.business_id == UUID(business_id),
                DecisionLogModel.conversation_id == conversation_id,
            )
            .order_by(DecisionLogModel.created_at.asc())
        )
        result = await self._session.execute(statement)

        return [
            DecisionRecord(
                tenant_id=tenant_id,
                business_id=business_id,
                conversation_id=conversation_id,
                agent_id=row.agent_id,
                action=InferenceAction(row.action),
                source=row.source,
                intent=row.intent,
                similarity=row.similarity,
                matched_question=row.matched_question,
                latency_ms=row.latency_ms,
                created_at=row.created_at,
            )
            for row in result.scalars()
        ]

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
