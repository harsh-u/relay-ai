from abc import ABC, abstractmethod

from backend.app.domain.users.user import User


class UserRepository(ABC):
    """Finds and creates human users authenticated via OAuth."""

    @abstractmethod
    async def find_by_oauth_identity(self, provider: str, subject: str) -> User | None:
        """Look up a user by their (provider, subject) OAuth identity -
        the stable pair that identifies the same real person on every
        subsequent login, even if their email address later changes."""
        raise NotImplementedError

    @abstractmethod
    async def create(self, email: str, provider: str, subject: str) -> User:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        raise NotImplementedError
