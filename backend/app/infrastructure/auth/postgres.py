from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.auth.api_key import ApiKey
from backend.app.domain.auth.hashing import display_prefix, generate_raw_key, hash_key
from backend.app.domain.auth.repository import ApiKeyRepository
from backend.app.models.api_key import ApiKeyModel


class PostgresApiKeyRepository(ApiKeyRepository):
    """PostgreSQL-backed API key store."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str) -> tuple[ApiKey, str]:
        raw_key = generate_raw_key()

        model = ApiKeyModel(
            tenant_id=UUID(tenant_id),
            key_hash=hash_key(raw_key),
            key_prefix=display_prefix(raw_key),
        )
        self._session.add(model)
        await self._session.flush()

        return self._to_domain(model), raw_key

    async def find_active_by_hash(self, key_hash: str) -> ApiKey | None:
        statement = select(ApiKeyModel).where(
            ApiKeyModel.key_hash == key_hash,
            ApiKeyModel.revoked_at.is_(None),
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        return self._to_domain(model) if model is not None else None

    async def list_for_tenant(self, tenant_id: str) -> list[ApiKey]:
        statement = (
            select(ApiKeyModel)
            .where(ApiKeyModel.tenant_id == UUID(tenant_id))
            .order_by(ApiKeyModel.created_at.desc())
        )
        result = await self._session.execute(statement)

        return [self._to_domain(model) for model in result.scalars()]

    def _to_domain(self, model: ApiKeyModel) -> ApiKey:
        return ApiKey(
            id=str(model.id),
            tenant_id=str(model.tenant_id),
            key_hash=model.key_hash,
            key_prefix=model.key_prefix,
            created_at=model.created_at,
            revoked_at=model.revoked_at,
        )
