from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from backend.app.domain.business.knowledge_scope import KnowledgeScope


class CreateCompanyRequest(BaseModel):
    """Create a new company (a tenant + its one business) - mainly for the
    test panel, so companies can be created without a direct DB insert."""

    name: str = Field(
        min_length=1,
        description="The company's display name.",
        examples=["Bright Smile Dental"],
    )

    @field_validator("name")
    @classmethod
    def _name_must_have_visible_content(cls, value: str) -> str:
        stripped = value.strip()

        if not stripped:
            raise ValueError("name cannot be blank")

        return stripped


class CompanyResponse(BaseModel):
    """A company - use `id` as this company's `business_id`, and `tenant_id`
    as its `tenant_id`, in every other RelayAI endpoint."""

    id: str = Field(description="This company's business_id for every other endpoint.")
    tenant_id: str = Field(description="This company's tenant_id for every other endpoint.")
    name: str
    slug: str
    knowledge_scope: KnowledgeScope
    knowledge_ttl_days: int
    created_at: datetime
    api_key: str | None = Field(
        default=None,
        description=(
            "This tenant's newly minted API key - present ONLY in the "
            "response to POST /v1/companies, and only for the company just "
            "created. Never returned again by this or any other call "
            "(GET/DELETE /v1/companies always send this as null) - copy it "
            "now. Use it as 'Authorization: Bearer <api_key>' on every "
            "other RelayAI endpoint."
        ),
    )


class ListCompaniesResponse(BaseModel):
    """Every company that exists, newest first."""

    companies: list[CompanyResponse]


class DeleteCompanyResponse(BaseModel):
    """Whether a matching company existed and was deleted."""

    deleted: bool


class MintApiKeyResponse(BaseModel):
    """A freshly minted API key for a company that already exists - the
    same one-time-reveal contract as the api_key field on CompanyResponse:
    copy it now, it's never returned again."""

    api_key: str = Field(description="The new raw API key - shown once, here.")
    key_prefix: str = Field(description="The key's first few characters, for display later.")
    created_at: datetime
