from backend.app.infrastructure.users.in_memory import InMemoryUserRepository


async def test_create_returns_a_new_user() -> None:
    repository = InMemoryUserRepository()

    user = await repository.create(email="alice@example.com", provider="google", subject="sub-1")

    assert user.email == "alice@example.com"
    assert user.oauth_provider == "google"
    assert user.oauth_subject == "sub-1"


async def test_find_by_oauth_identity_finds_the_right_user() -> None:
    repository = InMemoryUserRepository()
    created = await repository.create(email="alice@example.com", provider="google", subject="s1")
    await repository.create(email="bob@example.com", provider="google", subject="s2")

    found = await repository.find_by_oauth_identity("google", "s1")

    assert found is not None
    assert found.id == created.id


async def test_find_by_oauth_identity_is_scoped_to_the_provider() -> None:
    """Same subject value, different provider - must not collide."""
    repository = InMemoryUserRepository()
    await repository.create(email="alice@example.com", provider="google", subject="42")

    found = await repository.find_by_oauth_identity("github", "42")

    assert found is None


async def test_find_by_oauth_identity_returns_none_when_unknown() -> None:
    repository = InMemoryUserRepository()

    found = await repository.find_by_oauth_identity("google", "never-seen")

    assert found is None


async def test_get_by_id_returns_the_matching_user() -> None:
    repository = InMemoryUserRepository()
    created = await repository.create(email="alice@example.com", provider="google", subject="s1")

    found = await repository.get_by_id(created.id)

    assert found is not None
    assert found.email == "alice@example.com"


async def test_get_by_id_returns_none_for_an_unknown_id() -> None:
    repository = InMemoryUserRepository()

    found = await repository.get_by_id("00000000-0000-0000-0000-000000000000")

    assert found is None
