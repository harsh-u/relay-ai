from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ApiKey:
    """One issued API key for a tenant, for Bearer-token authentication.
    Only `key_hash` identifies it going forward - the raw key itself is
    handed back exactly once, at creation, and never persisted anywhere."""

    id: str
    tenant_id: str
    key_hash: str
    key_prefix: str
    created_at: datetime
    revoked_at: datetime | None

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None
