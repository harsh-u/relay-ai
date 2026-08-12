from abc import ABC, abstractmethod

from backend.app.domain.auth.api_key import ApiKey


class ApiKeyRepository(ABC):
    """Mints and looks up tenant-scoped API keys for Bearer-token
    authentication. One tenant can hold multiple active keys at once
    (rotation-friendly) - there is deliberately no `revoke()` here yet;
    revocation is an explicit fast-follow, not in scope for this pass."""

    @abstractmethod
    async def create(self, tenant_id: str) -> tuple[ApiKey, str]:
        """Mint and persist a new active key for this tenant. Returns the
        persisted record and the one-time raw key - the raw key is never
        retrievable again after this call returns; only its hash is kept."""
        raise NotImplementedError

    @abstractmethod
    async def find_active_by_hash(self, key_hash: str) -> ApiKey | None:
        """Look up a non-revoked key by its sha256 hash, or None if no such
        active key exists (unknown hash, or a real key that's been
        revoked)."""
        raise NotImplementedError

    @abstractmethod
    async def list_for_tenant(self, tenant_id: str) -> list[ApiKey]:
        """List every key (active or revoked) for a tenant, newest first."""
        raise NotImplementedError
