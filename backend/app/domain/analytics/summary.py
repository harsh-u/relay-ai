from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class DecisionSummary:
    """Aggregate view of how often RelayAI avoided the LLM for a business."""

    total: int
    respond_count: int
    fallback_count: int
    respond_by_source: dict[str, int] = field(default_factory=dict)

    @property
    def avoided_llm_rate(self) -> float:
        """Share of requests answered without falling back to the LLM."""
        if self.total == 0:
            return 0.0

        return self.respond_count / self.total
