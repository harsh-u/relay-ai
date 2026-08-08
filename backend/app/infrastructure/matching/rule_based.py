from backend.app.domain.matching.intent import Intent
from backend.app.domain.text.normalizer import normalize_text


class RuleBasedIntentMatcher:
    """Simple local intent matcher used as the first RelayAI matcher."""

    _patterns: dict[Intent, tuple[str, ...]] = {
        Intent.GREETING: (
            "hi",
            "hello",
            "hey",
            "hi there",
            "hello there",
            "hey there",
        ),
        Intent.REPEAT_REQUEST: (
            "repeat",
            "repeat that",
            "repeat it",
            "say that again",
            "say it again",
            "can you repeat that",
            "could you repeat that",
            "could you say that again",
            "please repeat",
            "i didn't hear that",
            "i did not hear that",
        ),
    }

    async def match(self, text: str) -> Intent | None:
        """Match normalized user text against known intent patterns."""

        normalized = normalize_text(text)

        if not normalized:
            return None

        for intent, patterns in self._patterns.items():
            if normalized in patterns:
                return intent

        return None
