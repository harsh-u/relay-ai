from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.conversation.message import ConversationMessage
from backend.app.domain.conversation.scope import ConversationScope
from backend.app.domain.conversation.store import ConversationStore
from backend.app.domain.conversation.summary import ConversationSummary
from backend.app.models.conversation_message import ConversationMessageModel


class PostgresConversationStore(ConversationStore):
    """PostgreSQL-backed conversation store."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _save(self, scope: ConversationScope, role: str, text: str) -> None:
        message = ConversationMessageModel(
            tenant_id=UUID(scope.tenant_id),
            business_id=UUID(scope.business_id),
            conversation_id=scope.conversation_id,
            role=role,
            text=text,
        )

        self._session.add(message)
        await self._session.flush()

    async def save_user_message(
        self,
        scope: ConversationScope,
        text: str,
    ) -> None:
        await self._save(scope, "user", text)

    async def save_assistant_response(
        self,
        scope: ConversationScope,
        text: str,
    ) -> None:
        await self._save(scope, "assistant", text)

    async def get_last_assistant_response(
        self,
        scope: ConversationScope,
    ) -> ConversationMessage | None:
        statement = (
            select(ConversationMessageModel)
            .where(
                ConversationMessageModel.tenant_id == UUID(scope.tenant_id),
                ConversationMessageModel.business_id == UUID(scope.business_id),
                ConversationMessageModel.conversation_id == scope.conversation_id,
                ConversationMessageModel.role == "assistant",
            )
            .order_by(ConversationMessageModel.created_at.desc())
            .limit(1)
        )

        result = await self._session.execute(statement)
        message = result.scalar_one_or_none()

        if message is None:
            return None

        return ConversationMessage(
            conversation_id=message.conversation_id,
            role=message.role,
            text=message.text,
            created_at=message.created_at,
        )

    async def get_recent_messages(
        self,
        scope: ConversationScope,
        limit: int = 20,
    ) -> list[ConversationMessage]:
        statement = (
            select(ConversationMessageModel)
            .where(
                ConversationMessageModel.tenant_id == UUID(scope.tenant_id),
                ConversationMessageModel.business_id == UUID(scope.business_id),
                ConversationMessageModel.conversation_id == scope.conversation_id,
            )
            .order_by(ConversationMessageModel.created_at.desc())
            .limit(limit)
        )

        result = await self._session.execute(statement)
        messages = result.scalars().all()

        return [
            ConversationMessage(
                conversation_id=message.conversation_id,
                role=message.role,
                text=message.text,
                created_at=message.created_at,
            )
            for message in reversed(messages)
        ]

    async def list_recent_conversations(
        self,
        tenant_id: str,
        business_id: str,
        limit: int = 20,
    ) -> list[ConversationSummary]:
        # DISTINCT ON (conversation_id), ordered within each group by
        # created_at desc, keeps only that conversation's latest message.
        latest_per_conversation = (
            select(ConversationMessageModel)
            .distinct(ConversationMessageModel.conversation_id)
            .where(
                ConversationMessageModel.tenant_id == UUID(tenant_id),
                ConversationMessageModel.business_id == UUID(business_id),
            )
            .order_by(
                ConversationMessageModel.conversation_id,
                ConversationMessageModel.created_at.desc(),
            )
            .subquery()
        )

        statement = (
            select(latest_per_conversation)
            .order_by(latest_per_conversation.c.created_at.desc())
            .limit(limit)
        )

        result = await self._session.execute(statement)

        return [
            ConversationSummary(
                conversation_id=row.conversation_id,
                last_message_role=row.role,
                last_message_text=row.text,
                last_message_at=row.created_at,
            )
            for row in result
        ]

    async def purge_expired(self, older_than: datetime) -> int:
        statement = delete(ConversationMessageModel).where(
            ConversationMessageModel.created_at < older_than
        )
        result = await self._session.execute(statement)
        await self._session.flush()

        return result.rowcount
