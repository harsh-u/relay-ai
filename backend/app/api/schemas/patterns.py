from pydantic import BaseModel, Field

from backend.app.domain.matching.intent import Intent


class AddPatternRequest(BaseModel):
    """A business-specific trigger phrase to add on top of RelayAI's builtin
    patterns for a known intent."""

    tenant_id: str = Field(
        min_length=1,
        description="The tenant this business belongs to.",
        examples=["11111111-1111-1111-1111-111111111111"],
    )
    business_id: str = Field(
        min_length=1,
        description="The business this custom pattern applies to.",
        examples=["22222222-2222-2222-2222-222222222222"],
    )
    intent: Intent = Field(
        description="Which known intent this phrase should trigger.",
        examples=["greeting"],
    )
    pattern: str = Field(
        min_length=1,
        description=(
            "The phrase itself, normalized the same way user speech is "
            "(lowercased, punctuation stripped) before matching."
        ),
        examples=["yo"],
    )


class AddPatternResponse(BaseModel):
    """Confirmation that the pattern is now in effect for this business.

    Adding the same (intent, pattern) twice is a no-op, not an error."""

    stored: bool = True


class PatternItem(BaseModel):
    """One of a business's own custom patterns (not RelayAI's builtins)."""

    intent: Intent
    pattern: str


class ListPatternsResponse(BaseModel):
    """A business's own custom patterns - not merged with builtin defaults,
    since the point of this endpoint is to see what a business added."""

    patterns: list[PatternItem]


class RemovePatternResponse(BaseModel):
    """Whether a matching custom pattern existed and was removed.

    RelayAI's builtin defaults can never be removed this way - only a
    business's own additions."""

    removed: bool
