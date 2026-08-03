"""Local, deterministic semantic similarity via fastembed (ONNX, no PyTorch).

Same design rule as the LLM provider: this is never the only scoring engine.
Every failure path (disabled, package missing, model download fails, empty
input) returns ``None`` so the caller falls back to the LLM/rule-based score.
The model is loaded lazily and cached process-wide — the first evaluation after
boot pays the load cost, subsequent ones are fast.
"""

from app.core.config import get_settings

_model = None
_load_failed = False


def _get_model():
    global _model, _load_failed
    if _model is not None or _load_failed:
        return _model
    try:
        import os

        from fastembed import TextEmbedding

        settings = get_settings()
        os.makedirs(settings.embeddings_cache_dir, exist_ok=True)
        # Persisted cache_dir means the model downloads once and survives restarts.
        _model = TextEmbedding(model_name=settings.embeddings_model, cache_dir=settings.embeddings_cache_dir)
    except Exception:
        # Package not installed or model could not be downloaded/loaded.
        _load_failed = True
        _model = None
    return _model


def embedding_similarity(text_a: str | None, text_b: str | None) -> float | None:
    """Cosine similarity of two texts mapped to a 0-100 score, or None.

    Returns None when embeddings are disabled, the model is unavailable, or
    either text is empty — signalling the caller to fall back.
    """
    settings = get_settings()
    if not settings.embeddings_enabled:
        return None
    if not (text_a and text_a.strip()) or not (text_b and text_b.strip()):
        return None

    model = _get_model()
    if model is None:
        return None

    try:
        import numpy as np

        vectors = list(model.embed([text_a, text_b]))
        vec_a, vec_b = np.asarray(vectors[0]), np.asarray(vectors[1])
        norm = float(np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
        if norm == 0.0:
            return None
        cosine = float(np.dot(vec_a, vec_b) / norm)
        return round(max(0.0, cosine) * 100, 2)
    except Exception:
        return None
