from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.schemas.companies import (
    CompanyResponse,
    CreateCompanyRequest,
    ListCompaniesResponse,
)
from backend.app.application.onboarding import CompanyOnboardingService
from backend.app.domain.auth.repository import ApiKeyRepository
from backend.app.domain.business.company import Company
from backend.app.domain.business.company_repository import CompanyRepository
from backend.app.domain.users.user import User
from backend.app.infrastructure.auth.dependencies import get_api_key_repository
from backend.app.infrastructure.business.dependencies import get_company_repository
from backend.app.infrastructure.users.dependencies import require_current_user_for_api

router = APIRouter(prefix="/v1/me", tags=["me"])


def _to_response(company: Company, api_key: str | None = None) -> CompanyResponse:
    return CompanyResponse(
        id=company.id,
        tenant_id=company.tenant_id,
        name=company.name,
        slug=company.slug,
        knowledge_scope=company.knowledge_scope,
        knowledge_ttl_days=company.knowledge_ttl_days,
        created_at=company.created_at,
        api_key=api_key,
    )


@router.get("")
async def get_me(
    current_user: Annotated[User, Depends(require_current_user_for_api)],
) -> dict[str, str]:
    """The signed-in user's own identity."""
    return {"email": current_user.email}


@router.get("/companies", response_model=ListCompaniesResponse)
async def list_my_companies(
    current_user: Annotated[User, Depends(require_current_user_for_api)],
    company_repository: Annotated[CompanyRepository, Depends(get_company_repository)],
) -> ListCompaniesResponse:
    """List only the companies the signed-in user owns - unlike the
    internal panel's GET /v1/companies, which lists every company that
    exists."""

    companies = await company_repository.list_for_owner(current_user.id)

    return ListCompaniesResponse(companies=[_to_response(company) for company in companies])


@router.post("/companies", response_model=CompanyResponse)
async def create_my_company(
    request: CreateCompanyRequest,
    current_user: Annotated[User, Depends(require_current_user_for_api)],
    company_repository: Annotated[CompanyRepository, Depends(get_company_repository)],
    api_key_repository: Annotated[ApiKeyRepository, Depends(get_api_key_repository)],
) -> CompanyResponse:
    """Create a company owned by the signed-in user and mint its first
    API key - the self-service equivalent of the internal panel's open
    POST /v1/companies, scoped to whoever is actually logged in."""

    onboarding_service = CompanyOnboardingService(company_repository, api_key_repository)
    company, raw_api_key = await onboarding_service.create_company_with_key(
        name=request.name,
        owner_user_id=current_user.id,
    )

    return _to_response(company, api_key=raw_api_key)
