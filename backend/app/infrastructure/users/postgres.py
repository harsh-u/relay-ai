from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.users.repository import UserRepository
from backend.app.domain.users.user import User
from backend.app.models.user import UserModel


class PostgresUserRepository(UserRepository):
    """PostgreSQL-backed user store."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_oauth_identity(self, provider: str, subject: str) -> User | None:
        statement = select(UserModel).where(
            UserModel.oauth_provider == provider,
            UserModel.oauth_subject == subject,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        return self._to_domain(model) if model is not None else None

    async def create(self, email: str, provider: str, subject: str) -> User:
        model = UserModel(email=email, oauth_provider=provider, oauth_subject=subject)
        self._session.add(model)
        await self._session.flush()

        return self._to_domain(model)

    async def get_by_id(self, user_id: str) -> User | None:
        model = await self._session.get(UserModel, UUID(user_id))

        return self._to_domain(model) if model is not None else None

    def _to_domain(self, model: UserModel) -> User:
        return User(
            id=str(model.id),
            email=model.email,
            oauth_provider=model.oauth_provider,
            oauth_subject=model.oauth_subject,
            created_at=model.created_at,
        )
