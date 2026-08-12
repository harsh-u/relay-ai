from dataclasses import replace

from backend.app.domain.auth.hashing import hash_key
from backend.app.infrastructure.auth.in_memory import InMemoryApiKeyRepository

TENANT_ID = "tenant-1"
OTHER_TENANT_ID = "tenant-2"


async def test_create_returns_a_record_and_a_matching_raw_key() -> None:
    repository = InMemoryApiKeyRepository()

    api_key, raw_key = await repository.create(tenant_id=TENANT_ID)

    assert api_key.tenant_id == TENANT_ID
    assert api_key.is_active is True
    assert raw_key.startswith("rk_")
    assert api_key.key_prefix == raw_key[:8]


async def test_find_active_by_hash_finds_a_key_by_its_raw_key_hash() -> None:
    repository = InMemoryApiKeyRepository()
    api_key, raw_key = await repository.create(tenant_id=TENANT_ID)

    found = await repository.find_active_by_hash(hash_key(raw_key))

    assert found is not None
    assert found.id == api_key.id


async def test_find_active_by_hash_returns_none_for_an_unknown_hash() -> None:
    repository = InMemoryApiKeyRepository()

    found = await repository.find_active_by_hash("not-a-real-hash")

    assert found is None


async def test_find_active_by_hash_excludes_a_revoked_key() -> None:
    repository = InMemoryApiKeyRepository()
    api_key, raw_key = await repository.create(tenant_id=TENANT_ID)

    revoked_index = repository._keys.index(api_key)
    repository._keys[revoked_index] = replace(api_key, revoked_at=api_key.created_at)

    found = await repository.find_active_by_hash(hash_key(raw_key))

    assert found is None


async def test_list_for_tenant_returns_only_that_tenants_keys_newest_first() -> None:
    repository = InMemoryApiKeyRepository()

    first, _ = await repository.create(tenant_id=TENANT_ID)
    second, _ = await repository.create(tenant_id=TENANT_ID)
    await repository.create(tenant_id=OTHER_TENANT_ID)

    listed = await repository.list_for_tenant(TENANT_ID)

    assert [key.id for key in listed] == [second.id, first.id]
