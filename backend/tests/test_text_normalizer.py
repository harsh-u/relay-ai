from backend.app.domain.text.normalizer import normalize_text


def test_normalize_text_lowercases_and_strips() -> None:
    assert normalize_text("  HELLO  ") == "hello"


def test_normalize_text_removes_punctuation() -> None:
    assert normalize_text("Can you repeat that?") == "can you repeat that"


def test_normalize_text_collapses_whitespace() -> None:
    assert normalize_text("Could   you   say   that   again?") == ("could you say that again")
