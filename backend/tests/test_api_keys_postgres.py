from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.auth.hashing import hash_key
from backend.app.infrastructure.auth.postgres import PostgresApiKeyRepository
from backend.app.models.api_key import ApiKeyModel
from backend.app.models.tenant import Tenant


async def _create_tenant(session: AsyncSession) -> str:
    """Insert a Tenant the api_keys FK can reference.

    Not committed - the enclosing db_session transaction is rolled back on
    teardown, so this never persists beyond a single test.
    """
    tenant = Tenant(name="Test Tenant", slug=f"test-tenant-{uuid4()}")
    session.add(tenant)
    await session.flush()

    return str(tenant.id)


async def test_create_returns_a_record_and_a_matching_raw_key(db_session: AsyncSession) -> None:
    tenant_id = await _create_tenant(db_session)
    repository = PostgresApiKeyRepository(db_session)

    api_key, raw_key = await repository.create(tenant_id=tenant_id)

    assert api_key.tenant_id == tenant_id
    assert api_key.is_active is True
    assert raw_key.startswith("rk_")
    assert api_key.key_prefix == raw_key[:8]
    assert api_key.key_hash == hash_key(raw_key)


async def test_find_active_by_hash_finds_a_key_by_its_raw_key_hash(
    db_session: AsyncSession,
) -> None:
    tenant_id = await _create_tenant(db_session)
    repository = PostgresApiKeyRepository(db_session)
    api_key, raw_key = await repository.create(tenant_id=tenant_id)

    found = await repository.find_active_by_hash(hash_key(raw_key))

    assert found is not None
    assert found.id == api_key.id


async def test_find_active_by_hash_returns_none_for_an_unknown_hash(
    db_session: AsyncSession,
) -> None:
    repository = PostgresApiKeyRepository(db_session)

    found = await repository.find_active_by_hash("not-a-real-hash")

    assert found is None


async def test_find_active_by_hash_excludes_a_revoked_key(db_session: AsyncSession) -> None:
    tenant_id = await _create_tenant(db_session)
    repository = PostgresApiKeyRepository(db_session)
    api_key, raw_key = await repository.create(tenant_id=tenant_id)

    await db_session.execute(
        update(ApiKeyModel)
        .where(ApiKeyModel.id == api_key.id)
        .values(revoked_at=api_key.created_at)
    )
    await db_session.flush()

    found = await repository.find_active_by_hash(hash_key(raw_key))

    assert found is None


async def test_list_for_tenant_returns_only_that_tenants_keys_newest_first(
    db_session: AsyncSession,
) -> None:
    tenant_id = await _create_tenant(db_session)
    other_tenant_id = await _create_tenant(db_session)
    repository = PostgresApiKeyRepository(db_session)

    first, _ = await repository.create(tenant_id=tenant_id)
    second, _ = await repository.create(tenant_id=tenant_id)
    await repository.create(tenant_id=other_tenant_id)

    listed = await repository.list_for_tenant(tenant_id)

    assert [key.id for key in listed] == [second.id, first.id]
