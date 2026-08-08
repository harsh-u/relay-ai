from difflib import SequenceMatcher

from backend.app.domain.matching.builtin_patterns import BUILTIN_PATTERNS
from backend.app.domain.matching.intent import Intent
from backend.app.domain.text.normalizer import normalize_text

# Chosen so real paraphrases/typos ("sorry can you repeat", "plz repeat") still
# match while business questions that happen to share short words with a
# builtin pattern ("is anyone there" ~0.61, "can you help me with billing"
# ~0.55) do not. A false negative just falls through to the LLM; a false
# positive silently answers the wrong thing, so this favors precision over recall.
FUZZY_MATCH_THRESHOLD = 0.70


class RuleBasedIntentMatcher:
    """Matches user text to a known intent by exact phrase, then by similarity."""

    def __init__(self, patterns: dict[Intent, tuple[str, ...]] | None = None) -> None:
        self._patterns = patterns if patterns is not None else BUILTIN_PATTERNS

    async def match(self, text: str) -> Intent | None:
        """Match normalized user text against known intent patterns.

        Tries an exact match first. If nothing matches exactly, falls back to
        the closest pattern by string similarity, to catch paraphrases and
        typos (e.g. "can u repeat that").
        """

        normalized = normalize_text(text)

        if not normalized:
            return None

        for intent, patterns in self._patterns.items():
            if normalized in patterns:
                return intent

        best_intent: Intent | None = None
        best_ratio = 0.0

        for intent, patterns in self._patterns.items():
            for pattern in patterns:
                ratio = SequenceMatcher(None, normalized, pattern).ratio()

                if ratio > best_ratio:
                    best_ratio = ratio
                    best_intent = intent

        if best_ratio >= FUZZY_MATCH_THRESHOLD:
            return best_intent

        return None
