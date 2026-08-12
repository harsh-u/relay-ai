from fastapi.testclient import TestClient


def test_missing_authorization_header_is_rejected(client_with_real_auth: TestClient) -> None:
    response = client_with_real_auth.post(
        "/v1/inference",
        json={"business_id": "business-1", "conversation_id": "c-1", "text": "hello"},
    )

    assert response.status_code == 401


def test_malformed_authorization_header_is_rejected(client_with_real_auth: TestClient) -> None:
    """A non-Bearer scheme (or an empty token) is indistinguishable from a
    missing header to HTTPBearer itself - both fall into the same 401
    branch, so this asserts the same status code, not a different message."""

    response = client_with_real_auth.post(
        "/v1/inference",
        json={"business_id": "business-1", "conversation_id": "c-1", "text": "hello"},
        headers={"Authorization": "Basic not-a-bearer-token"},
    )

    assert response.status_code == 401


def test_unknown_api_key_is_rejected(client_with_real_auth: TestClient) -> None:
    response = client_with_real_auth.post(
        "/v1/inference",
        json={"business_id": "business-1", "conversation_id": "c-1", "text": "hello"},
        headers={"Authorization": "Bearer rk_this_key_was_never_issued"},
    )

    assert response.status_code == 401


def test_a_freshly_minted_key_authenticates_successfully(
    client_with_real_auth: TestClient,
) -> None:
    company = client_with_real_auth.post(
        "/v1/companies", json={"name": "Auth Dependency Test Co"}
    ).json()

    response = client_with_real_auth.post(
        "/v1/inference",
        json={"business_id": company["id"], "conversation_id": "c-1", "text": "hello"},
        headers={"Authorization": f"Bearer {company['api_key']}"},
    )

    assert response.status_code == 200
    assert response.json()["action"] == "respond"
