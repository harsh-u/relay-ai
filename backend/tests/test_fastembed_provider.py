from pathlib import Path

import pytest

from backend.app.config.settings import get_settings
from backend.app.domain.embedding.similarity import cosine_similarity
from backend.app.infrastructure.embedding.fastembed_provider import FastEmbedProvider

_settings = get_settings()
_model_present = Path(_settings.embedding_model_dir).is_dir()

pytestmark = pytest.mark.skipif(
    not _model_present,
    reason=(
        f"Embedding model not found at {_settings.embedding_model_dir!r} - "
        "run scripts/export_embedding_model.py first"
    ),
)


@pytest.fixture(scope="module")
def provider() -> FastEmbedProvider:
    return FastEmbedProvider(model_dir=_settings.embedding_model_dir)


async def test_paraphrase_scores_higher_than_unrelated_question(
    provider: FastEmbedProvider,
) -> None:
    question = "Do you accept Delta Dental insurance?"
    paraphrase = "Is Delta Dental accepted here?"
    unrelated = "What time do you close on Saturdays?"

    query_vector, paraphrase_vector, unrelated_vector = await provider.embed(
        [question, paraphrase, unrelated]
    )

    paraphrase_similarity = cosine_similarity(query_vector, paraphrase_vector)
    unrelated_similarity = cosine_similarity(query_vector, unrelated_vector)

    assert paraphrase_similarity > _settings.embedding_similarity_threshold
    assert unrelated_similarity < _settings.embedding_similarity_threshold
    assert paraphrase_similarity - unrelated_similarity > 0.1


async def test_hindi_paraphrase_scores_higher_than_unrelated_question(
    provider: FastEmbedProvider,
) -> None:
    question = "क्या आप डेल्टा डेंटल इंश्योरेंस स्वीकार करते हैं?"
    paraphrase = "क्या यहाँ डेल्टा डेंटल स्वीकार किया जाता है?"
    unrelated = "आप शनिवार को कितने बजे बंद करते हैं?"

    query_vector, paraphrase_vector, unrelated_vector = await provider.embed(
        [question, paraphrase, unrelated]
    )

    paraphrase_similarity = cosine_similarity(query_vector, paraphrase_vector)
    unrelated_similarity = cosine_similarity(query_vector, unrelated_vector)

    assert paraphrase_similarity > _settings.embedding_similarity_threshold
    assert unrelated_similarity < _settings.embedding_similarity_threshold
