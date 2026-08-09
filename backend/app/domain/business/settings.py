from dataclasses import dataclass

from backend.app.domain.business.knowledge_scope import KnowledgeScope


@dataclass(frozen=True, slots=True)
class BusinessKnowledgeSettings:
    """A business's configuration for how its knowledge cache behaves."""

    knowledge_scope: KnowledgeScope
    knowledge_ttl_days: int
