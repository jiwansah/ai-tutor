from functools import lru_cache
from sentence_transformers import SentenceTransformer
from app.config import settings

@lru_cache
def _model():
    return SentenceTransformer(settings.EMBEDDING_MODEL)

def embed_text(text: str) -> list[float]:
    return _model().encode(text, normalize_embeddings=True).tolist()

def embed_batch(texts: list[str]) -> list[list[float]]:
    return _model().encode(texts, normalize_embeddings=True, batch_size=32).tolist()