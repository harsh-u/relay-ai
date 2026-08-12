from datetime import UTC, datetime
from uuid import uuid4

from backend.app.domain.auth.api_key import ApiKey
from backend.app.domain.auth.hashing import display_prefix, generate_raw_key, hash_key
from backend.app.domain.auth.repository import ApiKeyRepository


class InMemoryApiKeyRepository(ApiKeyRepository):
    def __init__(self) -> None:
        self._keys: list[ApiKey] = []

    async def create(self, tenant_id: str) -> tuple[ApiKey, str]:
        raw_key = generate_raw_key()
        api_key = ApiKey(
            id=str(uuid4()),
            tenant_id=tenant_id,
            key_hash=hash_key(raw_key),
            key_prefix=display_prefix(raw_key),
            created_at=datetime.now(UTC),
            revoked_at=None,
        )
        self._keys.append(api_key)
        return api_key, raw_key

    async def find_active_by_hash(self, key_hash: str) -> ApiKey | None:
        for api_key in self._keys:
            if api_key.key_hash == key_hash and api_key.is_active:
                return api_key

        return None

    async def list_for_tenant(self, tenant_id: str) -> list[ApiKey]:
        matching = [api_key for api_key in self._keys if api_key.tenant_id == tenant_id]
        return sorted(matching, key=lambda api_key: api_key.created_at, reverse=True)
