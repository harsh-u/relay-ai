from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.schemas.companies import (
    CompanyResponse,
    CreateCompanyRequest,
    ListCompaniesResponse,
)
from backend.app.domain.business.company import Company
from backend.app.domain.business.company_repository import CompanyRepository
from backend.app.infrastructure.business.dependencies import get_company_repository

router = APIRouter(
    prefix="/v1",
    tags=["companies"],
)


def _to_response(company: Company) -> CompanyResponse:
    return CompanyResponse(
        id=company.id,
        tenant_id=company.tenant_id,
        name=company.name,
        slug=company.slug,
        knowledge_scope=company.knowledge_scope,
        knowledge_ttl_days=company.knowledge_ttl_days,
        created_at=company.created_at,
    )


@router.post("/companies", response_model=CompanyResponse)
async def create_company(
    request: CreateCompanyRequest,
    company_repository: Annotated[
        CompanyRepository,
        Depends(get_company_repository),
    ],
) -> CompanyResponse:
    """Create a new company - a tenant + its one business, bundled together
    so the test panel (or any quick-start integration) doesn't need to think
    about multi-tenancy directly. Defaults to 'shared' knowledge scope and
    the global default TTL; use PATCH /v1/knowledge/settings to change
    either afterward."""

    company = await company_repository.create(name=request.name)

    return _to_response(company)


@router.get("/companies", response_model=ListCompaniesResponse)
async def list_companies(
    company_repository: Annotated[
        CompanyRepository,
        Depends(get_company_repository),
    ],
) -> ListCompaniesResponse:
    """List every company, newest first."""

    companies = await company_repository.list_all()

    return ListCompaniesResponse(companies=[_to_response(company) for company in companies])
