class FakeEmbeddingProvider:
    """Deterministic embedding provider for tests, no real model involved.

    Returns a fixed vector for texts registered via `set_vector`, and a
    distinct default vector for anything else, so tests can control exactly
    which texts should appear "similar" without depending on real semantic
    behavior.
    """

    def __init__(self) -> None:
        self._vectors: dict[str, list[float]] = {}

    def set_vector(self, text: str, vector: list[float]) -> None:
        self._vectors[text] = vector

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vectors.get(text, self._default_vector(text)) for text in texts]

    @staticmethod
    def _default_vector(text: str) -> list[float]:
        seed = sum(ord(character) for character in text) or 1
        return [float(seed % 97), float((seed * 7) % 89), float((seed * 13) % 83)]
