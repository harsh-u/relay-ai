import re
from dataclasses import dataclass
from datetime import datetime

from backend.app.domain.business.knowledge_scope import KnowledgeScope


@dataclass(frozen=True, slots=True)
class Company:
    """A tenant + its one business, bundled together for onboarding/testing
    - the unit a test panel thinks of as "a company"."""

    id: str
    tenant_id: str
    name: str
    slug: str
    knowledge_scope: KnowledgeScope
    knowledge_ttl_days: int
    created_at: datetime


def slugify(name: str) -> str:
    """Turn a display name into a URL/slug-safe lowercase form.

    Not guaranteed unique on its own - callers append a uniqueness suffix
    before persisting.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "company"
