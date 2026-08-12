"""Turns a provider's OAuth token/userinfo response into (email, subject) -
kept as small, pure(-ish) functions separate from the login route so this
part (unlike the actual redirect round-trip) can be unit tested without a
live Google/GitHub app."""

from typing import Any

from backend.app.infrastructure.oauth.client import (
    GITHUB_USER_API_URL,
    GITHUB_USER_EMAILS_API_URL,
)


class OAuthIdentityError(Exception):
    """Raised when a provider's response doesn't contain a usable,
    verified email address to sign in with."""


def extract_google_identity(token: dict[str, Any]) -> tuple[str, str]:
    """Google is OIDC - Authlib parses and validates the id_token into
    token["userinfo"] automatically when the 'openid' scope was granted,
    no extra network call needed."""

    userinfo = token.get("userinfo") or {}
    email = userinfo.get("email")
    subject = userinfo.get("sub")

    if not email or not subject:
        raise OAuthIdentityError("Google did not return an email/subject.")

    return email, str(subject)


async def extract_github_identity(oauth_client: Any, token: dict[str, Any]) -> tuple[str, str]:
    """GitHub is plain OAuth2, not OIDC - fetch the profile for the
    stable numeric user id, and the emails endpoint separately since
    /user's own `email` field is often null for users with a private
    email."""

    profile_response = await oauth_client.get(GITHUB_USER_API_URL, token=token)
    profile_response.raise_for_status()
    profile = profile_response.json()
    subject = profile.get("id")

    if subject is None:
        raise OAuthIdentityError("GitHub did not return a user id.")

    email = profile.get("email")

    if not email:
        email = await _fetch_github_primary_email(oauth_client, token)

    if not email:
        raise OAuthIdentityError("GitHub did not return a usable email.")

    return email, str(subject)


async def _fetch_github_primary_email(oauth_client: Any, token: dict[str, Any]) -> str | None:
    emails_response = await oauth_client.get(GITHUB_USER_EMAILS_API_URL, token=token)
    emails_response.raise_for_status()

    for entry in emails_response.json():
        if entry.get("primary") and entry.get("verified"):
            return entry.get("email")

    return None
