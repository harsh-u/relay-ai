import math

from backend.app.domain.embedding.similarity import cosine_similarity


def test_identical_vectors_have_similarity_one() -> None:
    vector = [1.0, 2.0, 3.0]

    assert math.isclose(cosine_similarity(vector, vector), 1.0)


def test_orthogonal_vectors_have_similarity_zero() -> None:
    assert math.isclose(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)


def test_opposite_vectors_have_similarity_negative_one() -> None:
    assert math.isclose(cosine_similarity([1.0, 0.0], [-1.0, 0.0]), -1.0)


def test_zero_vector_returns_zero_instead_of_dividing_by_zero() -> None:
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_is_scale_invariant() -> None:
    assert math.isclose(cosine_similarity([1.0, 2.0], [2.0, 4.0]), 1.0)
