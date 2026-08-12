from typing import Annotated

from fastapi import APIRouter, Depends, Path

from backend.app.api.schemas.companies import (
    CompanyResponse,
    CreateCompanyRequest,
    DeleteCompanyResponse,
    ListCompaniesResponse,
)
from backend.app.domain.auth.repository import ApiKeyRepository
from backend.app.domain.business.company import Company
from backend.app.domain.business.company_repository import CompanyRepository
from backend.app.infrastructure.auth.dependencies import get_api_key_repository
from backend.app.infrastructure.business.dependencies import get_company_repository

router = APIRouter(
    prefix="/v1",
    tags=["companies"],
)


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


@router.post("/companies", response_model=CompanyResponse)
async def create_company(
    request: CreateCompanyRequest,
    company_repository: Annotated[
        CompanyRepository,
        Depends(get_company_repository),
    ],
    api_key_repository: Annotated[
        ApiKeyRepository,
        Depends(get_api_key_repository),
    ],
) -> CompanyResponse:
    """Create a new company - a tenant + its one business, bundled together
    so the test panel (or any quick-start integration) doesn't need to think
    about multi-tenancy directly. Defaults to 'shared' knowledge scope and
    the global default TTL; use PATCH /v1/knowledge/settings to change
    either afterward.

    Also mints this tenant's first API key and returns it in `api_key` -
    shown exactly once, here. Every other RelayAI endpoint requires it as
    'Authorization: Bearer <api_key>'."""

    company = await company_repository.create(name=request.name)
    _, raw_api_key = await api_key_repository.create(tenant_id=company.tenant_id)

    return _to_response(company, api_key=raw_api_key)


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


@router.delete("/companies/{business_id}", response_model=DeleteCompanyResponse)
async def delete_company(
    business_id: Annotated[
        str, Path(description="The company's id (its business_id in every other endpoint).")
    ],
    company_repository: Annotated[
        CompanyRepository,
        Depends(get_company_repository),
    ],
) -> DeleteCompanyResponse:
    """Delete a company and everything under it - conversations, cached
    answers, custom patterns, decision history. Irreversible."""

    deleted = await company_repository.delete(business_id=business_id)

    return DeleteCompanyResponse(deleted=deleted)
