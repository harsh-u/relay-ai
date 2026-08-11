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


def test_created_company_is_usable_immediately_via_inference(client: TestClient) -> None:
    create_response = client.post("/v1/companies", json={"name": "Bright Smile Dental"})
    company = create_response.json()

    response = client.post(
        "/v1/inference",
        json={
            "tenant_id": company["tenant_id"],
            "business_id": company["id"],
            "conversation_id": "conv-new-company",
            "text": "hello",
        },
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
