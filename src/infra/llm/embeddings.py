"""The one place that turns text into vectors (local FastEmbed model, no API key), so the model changes only here."""

import os
import warnings
from functools import lru_cache
from pathlib import Path

from config.env import env

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")  # Windows without Developer Mode copies files instead: works fine
warnings.filterwarnings("ignore", message=".*now uses mean pooling.*")  # chunks and queries use the same pooling, so harmless

# Must match the model: the knowledge_chunk.embedding column is created with this many dimensions.
EMBEDDING_DIMENSIONS = 384
CACHE_DIR = Path(__file__).resolve().parents[3] / ".cache" / "fastembed"


@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding  # imported lazily: loading ONNX takes seconds and most processes never embed

    return TextEmbedding(env.embedding_model, cache_dir=str(CACHE_DIR))


def embed_texts(texts: list[str]) -> list[list[float]]:
    return [vector.tolist() for vector in _model().embed(texts)]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
