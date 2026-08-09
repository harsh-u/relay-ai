from enum import StrEnum


class KnowledgeScope(StrEnum):
    """Whether a business's agents share one knowledge cache or each get their own."""

    SHARED = "shared"
    ISOLATED = "isolated"
