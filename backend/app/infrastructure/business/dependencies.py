from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.settings import get_settings
from backend.app.db.session import get_db_session
from backend.app.domain.business.company_repository import CompanyRepository
from backend.app.domain.business.repository import BusinessSettingsRepository
from backend.app.infrastructure.business.postgres import PostgresBusinessSettingsRepository
from backend.app.infrastructure.business.postgres_company import PostgresCompanyRepository


async def get_business_settings_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BusinessSettingsRepository:
    """Provide the production business settings repository."""
    return PostgresBusinessSettingsRepository(
        session,
        default_ttl_days=get_settings().knowledge_cache_ttl_days,
    )


async def get_company_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyRepository:
    """Provide the production company repository."""
    return PostgresCompanyRepository(
        session,
        default_ttl_days=get_settings().knowledge_cache_ttl_days,
    )
