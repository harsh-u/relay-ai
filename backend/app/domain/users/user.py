from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class User:
    """A human who signed in via OAuth (Google or GitHub) - distinct from
    a Tenant/Business, which a User can create and own once logged in."""

    id: str
    email: str
    oauth_provider: str
    oauth_subject: str
    created_at: datetime
