from backend.app.domain.auth.repository import ApiKeyRepository
from backend.app.domain.business.company import Company
from backend.app.domain.business.company_repository import CompanyRepository


class CompanyOnboardingService:
    """Creates a company and mints its first API key together - the one
    place this pairing happens, so the open internal-panel endpoint and
    the session-authenticated dashboard endpoint can't drift apart."""

    def __init__(
        self,
        company_repository: CompanyRepository,
        api_key_repository: ApiKeyRepository,
    ) -> None:
        self._company_repository = company_repository
        self._api_key_repository = api_key_repository

    async def create_company_with_key(
        self,
        name: str,
        owner_user_id: str | None = None,
    ) -> tuple[Company, str]:
        company = await self._company_repository.create(name=name, owner_user_id=owner_user_id)
        _, raw_api_key = await self._api_key_repository.create(tenant_id=company.tenant_id)

        return company, raw_api_key
