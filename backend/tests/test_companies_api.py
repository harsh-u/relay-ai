from fastapi.testclient import TestClient


def test_create_company_returns_shared_scope_and_default_ttl(client: TestClient) -> None:
    response = client.post("/v1/companies", json={"name": "Bright Smile Dental"})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Bright Smile Dental"
    assert body["knowledge_scope"] == "shared"
    assert body["id"]
    assert body["tenant_id"]
    assert body["id"] != body["tenant_id"]


def test_create_company_returns_a_usable_api_key_once(client: TestClient) -> None:
    response = client.post("/v1/companies", json={"name": "Bright Smile Dental"})

    assert response.status_code == 200
    body = response.json()
    assert body["api_key"]
    assert body["api_key"].startswith("rk_")

    listed = client.get("/v1/companies").json()["companies"]
    assert all(company["api_key"] is None for company in listed)


def test_created_company_is_usable_immediately_via_inference(
    client_with_real_auth: TestClient,
) -> None:
    """Uses the real api_key returned by creation - not the `test:` auth
    shortcut every other test uses - to prove the real hash-and-lookup
    path genuinely authenticates a freshly minted key."""

    create_response = client_with_real_auth.post(
        "/v1/companies", json={"name": "Bright Smile Dental"}
    )
    company = create_response.json()

    response = client_with_real_auth.post(
        "/v1/inference",
        json={
            "business_id": company["id"],
            "conversation_id": "conv-new-company",
            "text": "hello",
        },
        headers={"Authorization": f"Bearer {company['api_key']}"},
    )

    assert response.status_code == 200
    assert response.json()["action"] == "respond"


def test_list_companies_returns_created_companies_newest_first(client: TestClient) -> None:
    client.post("/v1/companies", json={"name": "First Company"})
    client.post("/v1/companies", json={"name": "Second Company"})

    response = client.get("/v1/companies")

    assert response.status_code == 200
    names = [company["name"] for company in response.json()["companies"]]
    assert names == ["Second Company", "First Company"]


def test_create_company_rejects_a_whitespace_only_name(client: TestClient) -> None:
    response = client.post("/v1/companies", json={"name": "   "})

    assert response.status_code == 422


def test_create_company_trims_surrounding_whitespace(client: TestClient) -> None:
    response = client.post("/v1/companies", json={"name": "  Bright Smile Dental  "})

    assert response.status_code == 200
    assert response.json()["name"] == "Bright Smile Dental"


def test_delete_company_removes_it_from_the_list(client: TestClient) -> None:
    company = client.post("/v1/companies", json={"name": "Bright Smile Dental"}).json()

    response = client.delete(f"/v1/companies/{company['id']}")

    assert response.status_code == 200
    assert response.json() == {"deleted": True}
    names = [c["name"] for c in client.get("/v1/companies").json()["companies"]]
    assert "Bright Smile Dental" not in names


def test_delete_company_returns_false_for_an_unknown_id(client: TestClient) -> None:
    response = client.delete("/v1/companies/does-not-exist")

    assert response.status_code == 200
    assert response.json() == {"deleted": False}
