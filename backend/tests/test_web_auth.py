from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient

from backend.app.infrastructure.oauth.dependencies import get_oauth_registry
from backend.app.main import app


class _FakeOAuthClient:
    def __init__(self, token: dict) -> None:
        self._token = token

    async def authorize_redirect(self, request: object, redirect_uri: str) -> RedirectResponse:
        return RedirectResponse(url=f"{redirect_uri}?code=fake-code")

    async def authorize_access_token(self, request: object) -> dict:
        return self._token


class _FakeOAuthRegistry:
    def __init__(self, token: dict) -> None:
        self._token = token

    def create_client(self, name: str) -> _FakeOAuthClient:
        return _FakeOAuthClient(self._token)


def _override_oauth(token: dict) -> None:
    app.dependency_overrides[get_oauth_registry] = lambda: _FakeOAuthRegistry(token)


def _clear_oauth_override() -> None:
    del app.dependency_overrides[get_oauth_registry]


def test_login_page_renders(client: TestClient) -> None:
    response = client.get("/login")

    assert response.status_code == 200
    assert "Continue with Google" in response.text
    assert "Continue with GitHub" in response.text


def test_homepage_renders_without_login(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200


def test_homepage_redirects_to_dashboard_when_signed_in(authenticated_client) -> None:
    client, _ = authenticated_client

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"


def test_dashboard_redirects_to_login_when_not_signed_in(client: TestClient) -> None:
    response = client.get("/dashboard", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"].startswith("/login")


def test_dashboard_renders_when_signed_in(authenticated_client) -> None:
    client, _ = authenticated_client

    response = client.get("/dashboard")

    assert response.status_code == 200


def test_oauth_callback_signs_in_an_allowlisted_google_user(client: TestClient) -> None:
    token = {"userinfo": {"email": "harsh.raj@screen-magic.com", "sub": "google-sub-1"}}
    _override_oauth(token)
    try:
        response = client.get("/auth/google/callback?code=fake-code", follow_redirects=False)
    finally:
        _clear_oauth_override()

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"

    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200


def test_oauth_callback_denies_a_non_allowlisted_google_user(client: TestClient) -> None:
    token = {"userinfo": {"email": "not-allowed@example.com", "sub": "google-sub-2"}}
    _override_oauth(token)
    try:
        response = client.get("/auth/google/callback?code=fake-code")
    finally:
        _clear_oauth_override()

    assert response.status_code == 403
    assert "not on the beta list" in response.text


def test_oauth_callback_reuses_the_same_user_on_a_second_login(client: TestClient) -> None:
    token = {"userinfo": {"email": "harsh.raj@screen-magic.com", "sub": "google-sub-3"}}
    _override_oauth(token)
    try:
        client.get("/auth/google/callback?code=fake-code")
        first_dashboard = client.get("/v1/me").json()

        client.get("/auth/google/callback?code=fake-code")
        second_dashboard = client.get("/v1/me").json()
    finally:
        _clear_oauth_override()

    assert first_dashboard == second_dashboard


def test_oauth_start_stores_next_and_callback_redirects_there(client: TestClient) -> None:
    token = {"userinfo": {"email": "harsh.raj@screen-magic.com", "sub": "google-sub-next"}}
    _override_oauth(token)
    try:
        # follow_redirects=False: TestClient follows redirects by default,
        # which would immediately chase the fake authorize_redirect straight
        # into the callback within this same call, consuming oauth_next
        # before the test gets to make its own separate callback request.
        client.get("/auth/google/start?next=/console", follow_redirects=False)
        response = client.get("/auth/google/callback?code=fake-code", follow_redirects=False)
    finally:
        _clear_oauth_override()

    assert response.status_code == 302
    assert response.headers["location"] == "/console"


def test_oauth_callback_ignores_an_unsafe_next_path(client: TestClient) -> None:
    """`next` must only ever be a same-site relative path - an absolute
    URL would be an open redirect."""
    token = {"userinfo": {"email": "harsh.raj@screen-magic.com", "sub": "google-sub-unsafe"}}
    _override_oauth(token)
    try:
        client.get("/auth/google/start?next=https://evil.example.com", follow_redirects=False)
        response = client.get("/auth/google/callback?code=fake-code", follow_redirects=False)
    finally:
        _clear_oauth_override()

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"


def test_unknown_provider_is_rejected(client: TestClient) -> None:
    response = client.get("/auth/facebook/start")

    assert response.status_code == 404


def test_logout_clears_the_session(client: TestClient) -> None:
    """Uses the real session mechanism throughout (a real OAuth callback,
    then a real /logout) rather than the get_current_user_or_none
    override, which would bypass the session cookie entirely and prove
    nothing about logout actually clearing it."""

    token = {"userinfo": {"email": "harsh.raj@screen-magic.com", "sub": "google-sub-logout"}}
    _override_oauth(token)
    try:
        client.get("/auth/google/callback?code=fake-code")
        assert client.get("/dashboard").status_code == 200

        logout_response = client.post("/logout", follow_redirects=False)
        assert logout_response.status_code == 302

        response = client.get("/dashboard", follow_redirects=False)
    finally:
        _clear_oauth_override()

    assert response.status_code == 302
    assert response.headers["location"].startswith("/login")
