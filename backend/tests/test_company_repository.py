from backend.app.domain.business.company import slugify
from backend.app.domain.business.knowledge_scope import KnowledgeScope
from backend.app.infrastructure.business.in_memory_company import InMemoryCompanyRepository


def test_slugify_lowercases_and_replaces_non_alphanumerics() -> None:
    assert slugify("Bright Smile Dental!") == "bright-smile-dental"


def test_slugify_falls_back_to_a_default_for_an_empty_name() -> None:
    assert slugify("   ") == "company"


async def test_create_returns_a_company_with_shared_scope_and_default_ttl() -> None:
    repository = InMemoryCompanyRepository(default_ttl_days=30)

    company = await repository.create(name="Bright Smile Dental")

    assert company.name == "Bright Smile Dental"
    assert company.slug.startswith("bright-smile-dental-")
    assert company.knowledge_scope == KnowledgeScope.SHARED
    assert company.knowledge_ttl_days == 30
    assert company.id
    assert company.tenant_id
    assert company.id != company.tenant_id


async def test_create_gives_each_company_a_distinct_id_and_slug() -> None:
    repository = InMemoryCompanyRepository()

    first = await repository.create(name="Bright Smile Dental")
    second = await repository.create(name="Bright Smile Dental")

    assert first.id != second.id
    assert first.slug != second.slug


async def test_list_all_returns_every_company_newest_first() -> None:
    repository = InMemoryCompanyRepository()

    first = await repository.create(name="First Company")
    second = await repository.create(name="Second Company")

    companies = await repository.list_all()

    assert [company.id for company in companies] == [second.id, first.id]


async def test_delete_removes_an_existing_company() -> None:
    repository = InMemoryCompanyRepository()
    company = await repository.create(name="Bright Smile Dental")

    deleted = await repository.delete(company.id)

    assert deleted is True
    assert await repository.list_all() == []


async def test_delete_returns_false_for_an_unknown_company() -> None:
    repository = InMemoryCompanyRepository()

    deleted = await repository.delete("does-not-exist")

    assert deleted is False


async def test_delete_only_removes_the_targeted_company() -> None:
    repository = InMemoryCompanyRepository()
    first = await repository.create(name="First Company")
    second = await repository.create(name="Second Company")

    await repository.delete(first.id)

    remaining = await repository.list_all()
    assert [company.id for company in remaining] == [second.id]
