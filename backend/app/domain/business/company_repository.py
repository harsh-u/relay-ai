from abc import ABC, abstractmethod

from backend.app.domain.business.company import Company


class CompanyRepository(ABC):
    """Creates and lists companies - a tenant + its one business, bundled
    together for onboarding/testing without needing to think about
    multi-tenancy directly."""

    @abstractmethod
    async def create(self, name: str, owner_user_id: str | None = None) -> Company:
        """Create a company. `owner_user_id` is None for companies created
        through the open internal panel/API (unowned); set it when a
        logged-in human user creates their own company via the
        session-authenticated dashboard."""
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> list[Company]:
        """List every company, newest first."""
        raise NotImplementedError

    @abstractmethod
    async def list_for_owner(self, owner_user_id: str) -> list[Company]:
        """List only the companies owned by this user, newest first."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, business_id: str) -> Company | None:
        """Look up a single company by its business id, or None if no
        such company exists."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, business_id: str) -> bool:
        """Delete a company's business, and its tenant too if this was that
        tenant's only business (the common case, for a company created via
        `create()`). A tenant with other businesses under it - possible if
        one was added outside this repository - keeps the tenant and its
        other businesses. Returns True if the business existed."""
        raise NotImplementedError
