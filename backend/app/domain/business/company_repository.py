from abc import ABC, abstractmethod

from backend.app.domain.business.company import Company


class CompanyRepository(ABC):
    """Creates and lists companies - a tenant + its one business, bundled
    together for onboarding/testing without needing to think about
    multi-tenancy directly."""

    @abstractmethod
    async def create(self, name: str) -> Company:
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> list[Company]:
        """List every company, newest first."""
        raise NotImplementedError
