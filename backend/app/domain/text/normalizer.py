import re


def normalize_text(text: str) -> str:
    """Normalize user text before matching."""

    normalized = text.lower().strip()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized
