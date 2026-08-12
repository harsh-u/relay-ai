from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.business.knowledge_scope import KnowledgeScope
from backend.app.infrastructure.business.postgres_company import PostgresCompanyRepository
from backend.app.infrastructure.users.postgres import PostgresUserRepository
from backend.app.models.business import Business
from backend.app.models.tenant import Tenant


async def _create_user(session: AsyncSession, subject: str) -> str:
    user = await PostgresUserRepository(session).create(
        email=f"{subject}@example.com", provider="google", subject=subject
    )
    return user.id


async def test_create_persists_a_tenant_and_business_pair(db_session: AsyncSession) -> None:
    repository = PostgresCompanyRepository(db_session, default_ttl_days=30)

    company = await repository.create(name="Bright Smile Dental")

    assert UUID(company.id)
    assert UUID(company.tenant_id)
    assert company.id != company.tenant_id
    assert company.name == "Bright Smile Dental"
    assert company.knowledge_scope == KnowledgeScope.SHARED
    assert company.knowledge_ttl_days == 30


async def test_list_all_returns_created_companies_newest_first(db_session: AsyncSession) -> None:
    repository = PostgresCompanyRepository(db_session, default_ttl_days=30)

    first = await repository.create(name="First Company")
    second = await repository.create(name="Second Company")

    companies = await repository.list_all()

    ids = [company.id for company in companies]
    assert ids.index(second.id) < ids.index(first.id)


async def test_list_all_reads_a_ttl_of_zero_as_zero_not_the_default(
    db_session: AsyncSession,
) -> None:
    """0 is a deliberate, documented value ("never reuse cached answers"),
    not "unset" - it must not fall back to the default."""

    tenant = Tenant(name="Zero TTL Tenant", slug=f"zero-ttl-tenant-{uuid4()}")
    db_session.add(tenant)
    await db_session.flush()

    business = Business(
        tenant_id=tenant.id,
        name="Zero TTL Business",
        slug=f"zero-ttl-business-{uuid4()}",
        knowledge_ttl_days=0,
    )
    db_session.add(business)
    await db_session.flush()

    repository = PostgresCompanyRepository(db_session, default_ttl_days=30)
    companies = await repository.list_all()

    company = next(c for c in companies if c.id == str(business.id))
    assert company.knowledge_ttl_days == 0


async def test_delete_removes_the_business_and_its_now_orphaned_tenant(
    db_session: AsyncSession,
) -> None:
    repository = PostgresCompanyRepository(db_session, default_ttl_days=30)
    company = await repository.create(name="Bright Smile Dental")

    deleted = await repository.delete(company.id)

    assert deleted is True
    remaining_businesses = await db_session.execute(
        select(Business).where(Business.id == UUID(company.id))
    )
    assert remaining_businesses.scalar_one_or_none() is None
    remaining_tenants = await db_session.execute(
        select(Tenant).where(Tenant.id == UUID(company.tenant_id))
    )
    assert remaining_tenants.scalar_one_or_none() is None


async def test_delete_returns_false_for_an_unknown_business(db_session: AsyncSession) -> None:
    repository = PostgresCompanyRepository(db_session, default_ttl_days=30)

    deleted = await repository.delete(str(uuid4()))

    assert deleted is False


async def test_delete_keeps_the_tenant_when_it_has_other_businesses(
    db_session: AsyncSession,
) -> None:
    """A tenant created outside this repository can have more than one
    business under it - deleting one company must not take the others
    down with it."""

    repository = PostgresCompanyRepository(db_session, default_ttl_days=30)
    company = await repository.create(name="Bright Smile Dental")

    sibling_business = Business(
        tenant_id=UUID(company.tenant_id),
        name="Sibling Business",
        slug=f"sibling-business-{uuid4()}",
    )
    db_session.add(sibling_business)
    await db_session.flush()

    deleted = await repository.delete(company.id)

    assert deleted is True
    remaining_tenants = await db_session.execute(
        select(Tenant).where(Tenant.id == UUID(company.tenant_id))
    )
    assert remaining_tenants.scalar_one_or_none() is not None
    remaining_businesses = await db_session.execute(
        select(Business).where(Business.id == sibling_business.id)
    )
    assert remaining_businesses.scalar_one_or_none() is not None


async def test_create_without_an_owner_leaves_owner_user_id_none(db_session: AsyncSession) -> None:
    repository = PostgresCompanyRepository(db_session, default_ttl_days=30)

    company = await repository.create(name="Bright Smile Dental")

    assert company.owner_user_id is None


async def test_create_with_an_owner_records_it(db_session: AsyncSession) -> None:
    owner_id = await _create_user(db_session, "owner-1")
    repository = PostgresCompanyRepository(db_session, default_ttl_days=30)

    company = await repository.create(name="Bright Smile Dental", owner_user_id=owner_id)

    assert company.owner_user_id == owner_id


async def test_list_for_owner_returns_only_that_owners_companies(
    db_session: AsyncSession,
) -> None:
    owner_id = await _create_user(db_session, "owner-2")
    other_owner_id = await _create_user(db_session, "owner-3")
    repository = PostgresCompanyRepository(db_session, default_ttl_days=30)

    owned = await repository.create(name="Owned Co", owner_user_id=owner_id)
    await repository.create(name="Someone Else's Co", owner_user_id=other_owner_id)
    await repository.create(name="Unowned Co")

    companies = await repository.list_for_owner(owner_id)

    assert [company.id for company in companies] == [owned.id]


async def test_list_for_owner_is_empty_for_an_owner_with_no_companies(
    db_session: AsyncSession,
) -> None:
    owner_id = await _create_user(db_session, "owner-4")
    repository = PostgresCompanyRepository(db_session, default_ttl_days=30)

    companies = await repository.list_for_owner(owner_id)

    assert companies == []


async def test_get_by_id_returns_the_matching_company_with_its_owner(
    db_session: AsyncSession,
) -> None:
    owner_id = await _create_user(db_session, "owner-5")
    repository = PostgresCompanyRepository(db_session, default_ttl_days=30)
    company = await repository.create(name="Bright Smile Dental", owner_user_id=owner_id)

    found = await repository.get_by_id(company.id)

    assert found is not None
    assert found.id == company.id
    assert found.owner_user_id == owner_id


async def test_get_by_id_returns_none_for_an_unknown_company(db_session: AsyncSession) -> None:
    repository = PostgresCompanyRepository(db_session, default_ttl_days=30)

    found = await repository.get_by_id(str(uuid4()))

    assert found is None
