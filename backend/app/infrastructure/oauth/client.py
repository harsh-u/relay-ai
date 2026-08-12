from authlib.integrations.starlette_client import OAuth

from backend.app.config.settings import Settings

GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
GITHUB_USER_API_URL = "https://api.github.com/user"
GITHUB_USER_EMAILS_API_URL = "https://api.github.com/user/emails"


def build_oauth_registry(settings: Settings) -> OAuth:
    """Register the Google and GitHub OAuth2 clients Authlib will use for
    the login flow. Kept as a plain factory function (not a singleton) so
    tests can build their own registry with fake credentials, or swap in
    a fake OAuth client entirely via `get_oauth_registry`'s dependency
    override rather than talking to a real provider."""

    oauth = OAuth()

    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    oauth.register(
        name="github",
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        client_kwargs={"scope": "read:user user:email"},
    )

    return oauth
