import pytest

from backend.app.infrastructure.oauth.identity import (
    OAuthIdentityError,
    extract_github_identity,
    extract_google_identity,
)


def test_extract_google_identity_reads_email_and_subject_from_userinfo() -> None:
    token = {"userinfo": {"email": "alice@example.com", "sub": "12345"}}

    email, subject = extract_google_identity(token)

    assert email == "alice@example.com"
    assert subject == "12345"


def test_extract_google_identity_raises_when_userinfo_is_missing() -> None:
    with pytest.raises(OAuthIdentityError):
        extract_google_identity({})


def test_extract_google_identity_raises_when_email_is_missing() -> None:
    with pytest.raises(OAuthIdentityError):
        extract_google_identity({"userinfo": {"sub": "12345"}})


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


class _FakeGithubClient:
    def __init__(self, profile: dict, emails: list[dict]) -> None:
        self._profile = profile
        self._emails = emails

    async def get(self, url: str, token: dict) -> _FakeResponse:
        if url.endswith("/user/emails"):
            return _FakeResponse(self._emails)
        return _FakeResponse(self._profile)


async def test_extract_github_identity_uses_the_profiles_own_email_when_present() -> None:
    client = _FakeGithubClient(profile={"id": 42, "email": "bob@example.com"}, emails=[])

    email, subject = await extract_github_identity(client, token={})

    assert email == "bob@example.com"
    assert subject == "42"


async def test_extract_github_identity_falls_back_to_the_primary_verified_email() -> None:
    client = _FakeGithubClient(
        profile={"id": 42, "email": None},
        emails=[
            {"email": "secondary@example.com", "primary": False, "verified": True},
            {"email": "unverified@example.com", "primary": True, "verified": False},
            {"email": "primary@example.com", "primary": True, "verified": True},
        ],
    )

    email, subject = await extract_github_identity(client, token={})

    assert email == "primary@example.com"
    assert subject == "42"


async def test_extract_github_identity_raises_when_no_usable_email_exists() -> None:
    client = _FakeGithubClient(profile={"id": 42, "email": None}, emails=[])

    with pytest.raises(OAuthIdentityError):
        await extract_github_identity(client, token={})


async def test_extract_github_identity_raises_when_profile_has_no_id() -> None:
    client = _FakeGithubClient(profile={"email": "bob@example.com"}, emails=[])

    with pytest.raises(OAuthIdentityError):
        await extract_github_identity(client, token={})
