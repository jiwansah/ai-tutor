import httpx
from app.config import settings

_client = httpx.AsyncClient(timeout=60.0)


async def embed_text(text: str) -> list[float]:
    """Get a 768-d embedding from Ollama's nomic-embed-text."""
    if settings.EMBEDDING_PROVIDER != "ollama":
        return [0.0] * settings.EMBEDDING_DIM

    try:
        r = await _client.post(
            f"{settings.EMBEDDING_BASE_URL}/api/embeddings",
            json={"model": settings.EMBEDDING_MODEL, "prompt": text},
        )
        r.raise_for_status()
        emb = r.json().get("embedding", [])
        if len(emb) != settings.EMBEDDING_DIM:
            # Pad or truncate to match the vector column
            if len(emb) < settings.EMBEDDING_DIM:
                emb = emb + [0.0] * (settings.EMBEDDING_DIM - len(emb))
            else:
                emb = emb[: settings.EMBEDDING_DIM]
        return emb
    except Exception as e:
        print(f"[embedding] Ollama failed: {e}")
        return [0.0] * settings.EMBEDDING_DIM


async def embed_batch(texts: list[str]) -> list[list[float]]:
    out = []
    for t in texts:
        out.append(await embed_text(t))
    return out
