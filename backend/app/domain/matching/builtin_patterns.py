from backend.app.domain.matching.intent import Intent

BUILTIN_PATTERNS: dict[Intent, tuple[str, ...]] = {
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
