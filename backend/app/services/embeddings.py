"""Text embeddings for RAG.

- "hashing" (default): sklearn HashingVectorizer. No model download, works offline,
  lexical matching only. Good enough to get started.
- "fastembed": BAAI/bge-small-en-v1.5 semantic embeddings (384 dims). `pip install fastembed`.

Switching provider requires re-uploading documents (stored vectors are not comparable).
"""
import threading

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

from app.config import settings

_lock = threading.Lock()
_fastembed_model = None
_hasher = HashingVectorizer(
    n_features=settings.embedding_dim,
    alternate_sign=False,
    norm="l2",
    ngram_range=(1, 2),
    stop_words="english",
    lowercase=True,
)


def _fastembed():
    global _fastembed_model
    with _lock:
        if _fastembed_model is None:
            from fastembed import TextEmbedding  # optional dependency

            _fastembed_model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _fastembed_model


def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if settings.embedding_provider == "fastembed":
        vectors = np.array(list(_fastembed().embed(texts)), dtype=np.float32)
    else:
        vectors = _hasher.transform(texts).toarray().astype(np.float32)
    return vectors.tolist()


def is_zero(vector: list[float]) -> bool:
    return not any(vector)
