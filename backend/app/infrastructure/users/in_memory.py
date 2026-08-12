from datetime import UTC, datetime
from uuid import uuid4

from backend.app.domain.users.repository import UserRepository
from backend.app.domain.users.user import User


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: list[User] = []

    async def find_by_oauth_identity(self, provider: str, subject: str) -> User | None:
        for user in self._users:
            if user.oauth_provider == provider and user.oauth_subject == subject:
                return user

        return None

    async def create(self, email: str, provider: str, subject: str) -> User:
        user = User(
            id=str(uuid4()),
            email=email,
            oauth_provider=provider,
            oauth_subject=subject,
            created_at=datetime.now(UTC),
        )
        self._users.append(user)
        return user

    async def get_by_id(self, user_id: str) -> User | None:
        for user in self._users:
            if user.id == user_id:
                return user

        return None
