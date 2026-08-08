import asyncio
from pathlib import Path

from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType

_MODEL_NAME = "relayai/indic-sentence-bert-nli-int8"
_MODEL_FILE = "onnx/model_qint8_avx512_vnni.onnx"
_DIM = 768


def _ensure_model_registered() -> None:
    already_registered = any(
        model["model"] == _MODEL_NAME for model in TextEmbedding.list_supported_models()
    )

    if already_registered:
        return

    TextEmbedding.add_custom_model(
        model=_MODEL_NAME,
        pooling=PoolingType.MEAN,
        normalization=True,
        sources=ModelSource(hf="l3cube-pune/indic-sentence-bert-nli"),
        dim=_DIM,
        model_file=_MODEL_FILE,
    )


class FastEmbedProvider:
    """EmbeddingProvider backed by a local, quantized ONNX model via fastembed.

    Runs entirely on CPU through onnxruntime - no PyTorch at inference time.
    See scripts/export_embedding_model.py for how the model file is produced.
    """

    def __init__(self, model_dir: str) -> None:
        model_path = Path(model_dir)

        if not model_path.is_dir():
            raise RuntimeError(
                f"Embedding model directory not found: {model_path}. "
                "Run `python scripts/export_embedding_model.py` first "
                "(see that script's docstring for setup instructions)."
            )

        _ensure_model_registered()
        self._model = TextEmbedding(model_name=_MODEL_NAME, specific_model_path=str(model_path))

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._embed_sync, texts)

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(texts)]
