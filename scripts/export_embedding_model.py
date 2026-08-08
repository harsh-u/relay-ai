"""One-time offline conversion of the Indic sentence-embedding model to
quantized ONNX, so the running service only ever needs `fastembed` +
`onnxruntime` - never PyTorch.

This script itself needs `torch`, `optimum[onnxruntime]`, and
`sentence-transformers` - install those in a throwaway virtualenv, not the
project's own dependencies:

    python3 -m venv .export-venv
    .export-venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
    .export-venv/bin/pip install "optimum[onnxruntime]" sentence-transformers
    .export-venv/bin/python scripts/export_embedding_model.py

Output goes to `models/indic-sentence-bert-nli-int8/` (gitignored - see
.gitignore). Commit that directory to wherever the deployment target pulls
model artifacts from; it is not tracked in this git repo because of its size
(~230MB).
"""

import shutil
from pathlib import Path

from sentence_transformers import SentenceTransformer
from sentence_transformers.backend import export_dynamic_quantized_onnx_model

MODEL_NAME = "l3cube-pune/indic-sentence-bert-nli"
OUTPUT_DIR = Path(__file__).parent.parent / "models" / "indic-sentence-bert-nli-int8"


def main() -> None:
    print(f"Loading {MODEL_NAME} with the onnx backend (will export on first load)...")
    model = SentenceTransformer(MODEL_NAME, backend="onnx", model_kwargs={"export": True})
    print("Embedding dimension:", model.get_sentence_embedding_dimension())

    base_dir = OUTPUT_DIR.parent / f"{OUTPUT_DIR.name}-base-fp32"
    model.save_pretrained(str(base_dir))

    print("Quantizing to int8 (avx512_vnni)...")
    export_dynamic_quantized_onnx_model(
        model,
        quantization_config="avx512_vnni",
        model_name_or_path=str(OUTPUT_DIR),
    )

    print("Copying tokenizer/config files alongside the quantized weights...")
    for filename in (
        "config.json",
        "config_sentence_transformers.json",
        "modules.json",
        "sentence_bert_config.json",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.txt",
    ):
        shutil.copy(base_dir / filename, OUTPUT_DIR / filename)

    (OUTPUT_DIR / "1_Pooling").mkdir(exist_ok=True)
    shutil.copy(base_dir / "1_Pooling" / "config.json", OUTPUT_DIR / "1_Pooling" / "config.json")

    shutil.rmtree(base_dir)

    onnx_files = list((OUTPUT_DIR / "onnx").glob("*.onnx"))
    print(f"Done. Quantized model at {OUTPUT_DIR} ({onnx_files[0].name}).")


if __name__ == "__main__":
    main()
