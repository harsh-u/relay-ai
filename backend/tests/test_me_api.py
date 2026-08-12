from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.app.domain.users.user import User
from backend.app.infrastructure.users.dependencies import get_current_user_or_none
from backend.app.main import app


def test_get_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/v1/me")

    assert response.status_code == 401


def test_get_me_returns_the_signed_in_users_email(authenticated_client) -> None:
    client, user = authenticated_client

    response = client.get("/v1/me")

    assert response.status_code == 200
    assert response.json() == {"email": user.email}


def test_list_my_companies_is_empty_for_a_brand_new_user(authenticated_client) -> None:
    client, _ = authenticated_client

    response = client.get("/v1/me/companies")

    assert response.status_code == 200
    assert response.json() == {"companies": []}


def test_create_my_company_returns_a_usable_api_key(authenticated_client) -> None:
    client, _ = authenticated_client

    response = client.post("/v1/me/companies", json={"name": "Bright Smile Dental"})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Bright Smile Dental"
    assert body["api_key"]
    assert body["api_key"].startswith("rk_")


def test_created_company_then_appears_in_my_company_list(authenticated_client) -> None:
    client, _ = authenticated_client
    created = client.post("/v1/me/companies", json={"name": "Bright Smile Dental"}).json()

    response = client.get("/v1/me/companies")

    assert response.status_code == 200
    ids = [c["id"] for c in response.json()["companies"]]
    assert created["id"] in ids


def test_my_companies_are_not_visible_to_a_different_user(authenticated_client) -> None:
    client, _ = authenticated_client
    client.post("/v1/me/companies", json={"name": "Bright Smile Dental"})

    async def _other_user() -> User:
        return User(
            id="a-different-user",
            email="other@example.com",
            oauth_provider="google",
            oauth_subject="other-sub",
            created_at=datetime.now(UTC),
        )

    # Reassign (not delete) - `authenticated_client`'s own teardown still
    # owns removing this key once the test finishes.
    app.dependency_overrides[get_current_user_or_none] = _other_user
    response = client.get("/v1/me/companies")

    assert response.status_code == 200
    assert response.json() == {"companies": []}


def test_companies_created_via_me_do_not_appear_in_the_internal_open_endpoint_scoped_view(
    authenticated_client,
) -> None:
    """GET /v1/companies (internal panel) still lists everything - it's
    /v1/me/companies that's ownership-scoped, not the other way round."""
    client, _ = authenticated_client
    client.post("/v1/me/companies", json={"name": "Bright Smile Dental"})

    response = client.get("/v1/companies")

    assert response.status_code == 200
    names = [c["name"] for c in response.json()["companies"]]
    assert "Bright Smile Dental" in names
