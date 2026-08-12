from backend.app.config.settings import Settings


def is_email_allowed(email: str, settings: Settings) -> bool:
    """Whether this email may sign in during the closed beta.

    A static, comma-separated env var (`beta_allowlist_emails`) rather
    than a database table - deliberate MVP choice matching this
    project's existing "env var over new infra" pattern. Revisit if the
    allowlist needs to grow past a handful of manually-managed entries.
    """
    allowed = {
        allowed_email.strip().lower()
        for allowed_email in settings.beta_allowlist_emails.split(",")
        if allowed_email.strip()
    }

    return email.strip().lower() in allowed
