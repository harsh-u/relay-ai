from backend.app.config.settings import Settings
from backend.app.infrastructure.users.allowlist import is_email_allowed


def _settings(allowlist: str) -> Settings:
    return Settings(beta_allowlist_emails=allowlist)


def test_allows_an_exact_match() -> None:
    settings = _settings("alice@example.com,bob@example.com")

    assert is_email_allowed("alice@example.com", settings) is True


def test_denies_an_email_not_on_the_list() -> None:
    settings = _settings("alice@example.com")

    assert is_email_allowed("eve@example.com", settings) is False


def test_matching_is_case_insensitive() -> None:
    settings = _settings("Alice@Example.com")

    assert is_email_allowed("alice@example.com", settings) is True


def test_ignores_surrounding_whitespace_in_the_configured_list() -> None:
    settings = _settings(" alice@example.com , bob@example.com ")

    assert is_email_allowed("bob@example.com", settings) is True


def test_empty_allowlist_denies_everyone() -> None:
    settings = _settings("")

    assert is_email_allowed("alice@example.com", settings) is False
