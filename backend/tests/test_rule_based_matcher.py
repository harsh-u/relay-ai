import pytest

from backend.app.domain.matching.intent import Intent
from backend.app.infrastructure.matching.rule_based import RuleBasedIntentMatcher


@pytest.fixture
def matcher() -> RuleBasedIntentMatcher:
    return RuleBasedIntentMatcher()


@pytest.mark.parametrize(
    "text",
    [
        "Hello",
        "hi",
        "Hey there",
        "Can you repeat that?",
        "Could you say that again?",
        "please repeat",
    ],
)
async def test_exact_patterns_still_match(matcher: RuleBasedIntentMatcher, text: str) -> None:
    assert await matcher.match(text) is not None


@pytest.mark.parametrize(
    ("text", "expected_intent"),
    [
        ("heyy", Intent.GREETING),
        ("plz repeat", Intent.REPEAT_REQUEST),
        ("sorry can you repeat", Intent.REPEAT_REQUEST),
        ("can u repeat that", Intent.REPEAT_REQUEST),
        ("could u say that again", Intent.REPEAT_REQUEST),
    ],
)
async def test_fuzzy_paraphrases_are_matched(
    matcher: RuleBasedIntentMatcher, text: str, expected_intent: Intent
) -> None:
    assert await matcher.match(text) == expected_intent


@pytest.mark.parametrize(
    "text",
    [
        "What is your refund policy?",
        "good morning",
        "goodbye",
        "thank you",
        "is anyone there",
        "can you help me with billing",
        "i want to cancel my subscription",
        "speak to a manager",
    ],
)
async def test_unrelated_business_questions_do_not_false_positive(
    matcher: RuleBasedIntentMatcher, text: str
) -> None:
    assert await matcher.match(text) is None


async def test_empty_text_does_not_match(matcher: RuleBasedIntentMatcher) -> None:
    assert await matcher.match("   ") is None


async def test_custom_patterns_are_matched_exactly(matcher: RuleBasedIntentMatcher) -> None:
    custom_matcher = RuleBasedIntentMatcher(
        patterns={Intent.GREETING: ("yo",), Intent.REPEAT_REQUEST: ()}
    )

    assert await custom_matcher.match("yo") == Intent.GREETING
    assert await custom_matcher.match("hi") is None
